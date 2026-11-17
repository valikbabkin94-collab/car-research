import math
H=3600000
def atr_from_closed_hours(bars: list, published_ms: int) -> dict:
    """Same simple mean of 14 TRs as research; 15 contiguous closed 1h bars.

    Bybit rows are [open_ms, open, high, low, close,...]. Extra/future rows are
    discarded, never used for ATR or the reference price. Conflicts fail closed.
    """
    cutoff = int(published_ms) // H * H
    by = {}
    for row in bars:
        t = int(row[0])
        if t + H > cutoff:
            continue
        o, h, l, c = map(float, row[1:5])
        if t % H or not all(math.isfinite(v) and v > 0 for v in (o, h, l, c)) \
                or h < max(o, l, c) or l > min(o, h, c):
            raise ValueError('MANAGER_ATR_INVALID_BAR')
        b = (o, h, l, c)
        if t in by and by[t] != b:
            raise ValueError('MANAGER_ATR_CONFLICT')
        by[t] = b
    times = list(range(cutoff - 15 * H, cutoff, H))
    if not all(t in by for t in times):
        raise ValueError('MANAGER_ATR_DATA_GAP')
    b = [by[t] for t in times]
    atr = sum(max(b[i][1] - b[i][2], abs(b[i][1] - b[i-1][3]),
                  abs(b[i][2] - b[i-1][3])) for i in range(1, 15)) / 14
    if not math.isfinite(atr) or atr <= 0:
        raise ValueError('MANAGER_ATR_INVALID')
    return {'atr': atr, 'reference': b[-1][3], 'atr_hour_end_ms': cutoff}

def geometry(atr,ref,sign):
    distance = 1.5 * atr
    stop = ref - sign * distance
    targets = [ref + sign * i * distance for i in (1, 2, 3)]
    return distance,stop,targets

class Trade:pass
def _manager_source(s):return not s.get("_research_reversal",False)
class PureManager:
    def _commands_after_open(self,s,trade):return []
    def _be_delay_passed(self,trade,s):return True

    def _desired_stop(self, trade: Trade, s: dict) -> tuple[float, bool, float]:
            """Author SL (only tightened by author commands), BE+fees after TP1 / author BE."""
            is_long = not trade.is_short
            stop = float(s["stop"])
            cmds = self._commands_after_open(s, trade)
            for c in cmds:  # author moved the stop: only accept tightening
                if c["action"] == "SET_STOP" and c.get("price"):
                    p = float(c["price"])
                    stop = max(stop, p) if is_long else min(stop, p)
            want_be = ((self.cfg["move_be_after_tp1"] or _manager_source(s)) and trade.nr_of_successful_exits >= 1
                       and self._be_delay_passed(trade, s)) \
                or any(c["action"] == "MOVE_BE" for c in cmds)
            f = 0.0 if _manager_source(s) else 2 * self.cfg["fee_rate"]
            be = trade.open_rate * (1 + f) if is_long else trade.open_rate * (1 - f)
            if want_be:
                stop = max(stop, be) if is_long else min(stop, be)
            return stop, want_be, be

    def _reversal_exit(self, trade: Trade, s: dict, price: float, pair: str) -> str | None:
            if _manager_source(s):
                return None
            rv = self.cfg["reversal"]
            enabled = s.get("reversal_enabled") if s.get("reversal_enabled") is not None else rv.get("enabled")
            if not enabled:
                return None
            if s.get("reversal_mode") in ("blocks5m", "blocks"):
                return self._weak_trend_exit(trade, pair, int(s.get("block_min") or 5))
            if rv.get("after_tp1_only", True) and trade.nr_of_successful_exits < 1:
                return None
            is_long = not trade.is_short
            risk = abs(trade.open_rate - float(s["stop"]))
            best = (trade.max_rate if is_long else trade.min_rate) or trade.open_rate
            move = (best - trade.open_rate) if is_long else (trade.open_rate - best)
            if risk > 0 and move >= rv["min_move_r"] * risk:
                back = (best - price) if is_long else (price - best)
                if back / move >= rv["giveback"]:
                    return "reversal_giveback"
            n = int(rv.get("against_candles") or 0)
            tf = int(rv.get("against_tf_min") or 1)
            if n > 0 and rv.get("candles_need_move_r") and not (risk > 0 and move >= rv["candles_need_move_r"] * risk):
                n = 0          # owner 24.10 (research M1): candle reversal only after the trade made >= 1R
            if n > 0:
                df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if tf > 1 and len(df) > (n + 1) * tf:   # closed tf-minute blocks from 1m candles
                    closes = df["close"].iloc[-(n + 1) * tf - 1::tf].tolist()[-(n + 1):]
                else:
                    closes = df["close"].iloc[-(n + 1):].tolist() if len(df) > n else []
                if closes:
                    steps = [b - a for a, b in zip(closes, closes[1:])]
                    if all((x < 0) if is_long else (x > 0) for x in steps):
                        return "reversal_candles"
            return None
