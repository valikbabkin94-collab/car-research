"""Pure causal paper hypotheses. No network, filesystem, bot or order imports."""

import datetime as dt
import html
import math
import re
import statistics
from urllib.parse import urlsplit

H = 3600000


def contiguous(b, n):
    return len(b) >= n and all(y[0] - x[0] == H for x, y in zip(b[-n:], b[-n + 1 :]))


def squeeze_signal(b, ticker, interval_minutes):
    if not contiguous(b, 24):
        return None
    try:
        rate = float(ticker["fundingRate"])
        minutes = float(interval_minutes)
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(rate) or not math.isfinite(minutes) or minutes <= 0:
        return None
    normalized = rate * 480 / minutes
    if normalized > -0.001:
        return None
    low = min(x[3] for x in b[-24:])
    if low <= 0 or min(x[3] for x in b[-6:]) < min(x[3] for x in b[-24:-6]):
        return None
    return {
        "stop": low * (1 - 1e-8),
        "funding_indicative": rate,
        "interval_minutes": minutes,
        "funding_8h_indicative": normalized,
        "funding_input_kind": "OBSERVED_TICKER_PREDICTION_NOT_SETTLED_CASH",
    }


def g3_rank(frames):
    values = []
    for sym, b in frames.items():
        if contiguous(b, 720):
            values.append((sum(x[6] for x in b[-720:]) / 720, sym))
    return [s for _, s in sorted(values, key=lambda x: (-x[0], x[1]))[:150]]


def g3_candidates(frames, btc):
    if len(btc) < 25:
        return {}
    ranked = g3_rank(frames)
    losers = []
    for sym in ranked:
        b = frames[sym]
        r24 = b[-1][4] / b[-25][4] - 1
        if r24 <= -0.08:
            losers.append((r24, sym))
    result = {}
    btc_r = btc[-1][4] / btc[-25][4] - 1
    for r24, sym in sorted(losers)[:10]:
        b = frames[sym]
        n = len(b)
        if b[-1][0] != btc[-1][0] or r24 - btc_r > -0.06 or not contiguous(b, 26):
            continue
        low = [x[3] for x in b]
        anchor = max(range(n - 24, n), key=lambda i: (-low[i], i))
        piv = []
        for j in range(max(2, anchor), n - 2):
            if low[j] <= min(low[j - 2 : j]) and low[j] <= min(low[j + 1 : j + 3]):
                piv.append(j)
        if len(piv) < 2 or low[piv[-1]] <= low[piv[-2]]:
            continue
        volume = sum(x[5] for x in b[anchor:])
        quote = sum(x[6] for x in b[anchor:])
        prior = statistics.median(x[5] for x in b[-25:-1])
        if volume <= 0 or b[-1][4] <= quote / volume or b[-1][5] < 1.5 * prior:
            continue
        result[sym] = {
            "stop": min(low[-24:]) * (1 - 1e-8),
            "close24ago": b[-25][4],
            "minimum24": min(low[-24:]),
            "r24": r24,
            "btc_r24": btc_r,
            "universe_kind": "OBSERVED_ALL_MARKET_720_CLOSED_H1_QUOTE_RANK",
        }
    return result


MONTHS = {
    name: i
    for i, name in enumerate(
        [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ],
        1,
    )
}
DATE = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(20\d{2}),?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?\s*UTC\b",
    re.I,
)


def parse_delisting(record, article, observed_ms):
    url = record.get("url", "")
    u = urlsplit(url)
    if (
        u.scheme != "https"
        or u.hostname != "announcements.bybit.com"
        or not u.path.startswith("/en/article/")
        or u.username
        or u.password
    ):
        return {"status": "REJECTED_UNOFFICIAL_SOURCE"}
    publication = record.get("dateTimestamp")
    if (
        not isinstance(publication, (int, float))
        or not math.isfinite(publication)
        or publication < 10**11
        or publication > observed_ms
    ):
        return {"status": "DATA_GAP_EXACT_PUBLICATION_TIME"}
    text = html.unescape(
        re.sub(
            "<[^>]+>",
            " ",
            re.sub(r"<script\b[^>]*>.*?</script>", " ", article, flags=re.S | re.I),
        )
    )
    text = " ".join(
        (
            record.get("title", "") + " " + record.get("description", "") + " " + text
        ).split()
    )
    if not re.search(r"(delist.*?perpetual|perpetual.*?delist)", text, re.I):
        return {"status": "REJECTED_NOT_PERPETUAL_DELISTING"}
    if re.search(r"temporar|migration|migrat", text, re.I):
        return {"status": "REJECTED_TEMPORARY_OR_MIGRATION"}
    symbols = sorted(set(re.findall(r"\b[A-Z0-9]{2,30}USDT\b", text)))
    deadlines = set()
    for m in DATE.finditer(text):
        context = text[max(0, m.start() - 260) : m.start()].lower()
        if not any(k in context for k in ["delist", "cease trading", "end trading"]):
            continue
        month = MONTHS[m[1][:3].title()]
        hour = int(m[4])
        minute = int(m[5] or 0)
        ap = (m[6] or "").upper()
        if ap:
            hour = hour % 12 + (12 if ap == "PM" else 0)
        try:
            stamp = int(
                dt.datetime(
                    int(m[3]), month, int(m[2]), hour, minute, tzinfo=dt.timezone.utc
                ).timestamp()
                * 1000
            )
        except ValueError:
            continue
        deadlines.add(stamp)
    if not symbols or len(deadlines) != 1:
        return {"status": "DATA_GAP_UNAMBIGUOUS_CONTRACT_OR_DELIST_TIME"}
    deadline = next(iter(deadlines)) - 24 * H
    first = (int(observed_ms) // 60000 + 1) * 60000
    status = (
        "ELIGIBLE"
        if first <= publication + H and deadline > first
        else "REJECTED_LATE_OR_TOO_CLOSE"
    )
    return {
        "status": status,
        "symbols": symbols,
        "publication_ms": int(publication),
        "observed_ms": observed_ms,
        "delist_ms": deadline + 24 * H,
        "exit_deadline_ms": deadline,
        "url": url,
    }
