# All closed LIVE trades (97, 23.10–17.11.2026), anonymised read-only export by Claude

Fields: source, coin, side, open/close (UTC), entry, initial_stop, stop_pct, exit_reason, exits[], net_R.
- `net_R` = realized_profit (all partial exits + fees) / (entry notional × stop distance).
- `exits[].frac` = filled / trade.amount where trade.amount is the amount REMAINING at close (Freqtrade shrinks it after partial exits), so fracs can exceed 1. Normalise by the sum of exit fills, e.g. HUMA 1.6667/1.0/0.6667 → 1/2.333/… of total.
- No quantities, notional, IDs, balances, chat ids.
