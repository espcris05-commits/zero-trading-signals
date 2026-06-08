#!/usr/bin/env python3
"""Public-data paper trading signal generator.
No API keys, no orders, no account access.
"""
import json, math, sys, time, urllib.parse, urllib.request
from pathlib import Path

SYMBOLS = sys.argv[1:] or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
INTERVAL = "1h"
LIMIT = 120
OUT = Path("business/trading-lab/signals.json")
MD = Path("business/trading-lab/signals.md")


def fetch_klines(symbol):
    qs = urllib.parse.urlencode({"symbol": symbol, "interval": INTERVAL, "limit": LIMIT})
    url = f"https://api.binance.com/api/v3/klines?{qs}"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())


def ema(values, period):
    k = 2 / (period + 1)
    cur = values[0]
    for v in values[1:]:
        cur = v * k + cur * (1 - k)
    return cur


def rsi(values, period=14):
    gains, losses = [], []
    for a, b in zip(values[-period-1:-1], values[-period:]):
        d = b - a
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def signal(symbol):
    rows = fetch_klines(symbol)
    closes = [float(x[4]) for x in rows]
    last = closes[-1]
    e20 = ema(closes[-60:], 20)
    e50 = ema(closes[-90:], 50)
    r = rsi(closes)
    prev_e20 = ema(closes[-61:-1], 20)
    prev_e50 = ema(closes[-91:-1], 50)
    crossed_up = prev_e20 <= prev_e50 and e20 > e50
    crossed_down = prev_e20 >= prev_e50 and e20 < e50
    if crossed_up and r < 70:
        action = "PAPER_LONG_SIGNAL"
        stop = last * 0.975
        take = last * 1.05
    elif crossed_down or r > 75:
        action = "PAPER_EXIT_OR_SHORTLIST"
        stop = None
        take = None
    else:
        action = "NO_TRADE"
        stop = None
        take = None
    return {
        "symbol": symbol,
        "price": round(last, 6),
        "ema20": round(e20, 6),
        "ema50": round(e50, 6),
        "rsi14": round(r, 2),
        "action": action,
        "paper_stop": round(stop, 6) if stop else None,
        "paper_take_profit": round(take, 6) if take else None,
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for sym in SYMBOLS:
        try:
            results.append(signal(sym))
        except Exception as e:
            results.append({"symbol": sym, "error": str(e), "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = ["# Paper Trading Signals", "", "No real orders. Public data only.", ""]
    for x in results:
        if "error" in x:
            lines.append(f"- {x['symbol']}: ERROR {x['error']}")
        else:
            lines.append(f"- {x['symbol']}: {x['action']} | price {x['price']} | EMA20 {x['ema20']} | EMA50 {x['ema50']} | RSI {x['rsi14']} | stop {x['paper_stop']} | tp {x['paper_take_profit']}")
    MD.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
