

import os
import requests
from datetime import datetime, timezone, timedelta

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

COINS = {
    "BTC-USDT": 0.50,
    "ETH-USDT": 0.20,
    "BNB-USDT": 0.10,
    "SOL-USDT": 0.10,
    "XRP-USDT": 0.10
}

def send(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=20
    )
    r.raise_for_status()

def candles(symbol):
    r = requests.get(
        "https://www.okx.com/api/v5/market/candles",
        params={"instId": symbol, "bar": "5m", "limit": "100"},
        timeout=20
    )
    r.raise_for_status()
    j = r.json()

    if j.get("code") != "0":
        raise RuntimeError(str(j))

    rows = [x for x in j["data"] if x[8] == "1"]
    rows.sort(key=lambda x: int(x[0]))

    if len(rows) < 30:
        raise RuntimeError("Candle tidak cukup: " + symbol)

    return {x[0]: x for x in rows}

def index_data():
    all_data = {s: candles(s) for s in COINS}
    common = set.intersection(
        *(set(v.keys()) for v in all_data.values())
    )
    times = sorted(common, key=int)[-60:]

    if len(times) < 30:
        raise RuntimeError("Data candle antar koin tidak cocok")

    values = []
    for t in times:
        value = 0.0
        for symbol, weight in COINS.items():
            value += weight * float(all_data[symbol][t][4])
        values.append(value)

    return values, times[-1]

def ema(values, period):
    alpha = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1-alpha) * result[-1])
    return result

def rsi(values, period=14):
    changes = [
        values[i] - values[i-1]
        for i in range(1, len(values))
    ]
    recent = changes[-period:]
    gains = sum(max(x, 0) for x in recent) / period
    losses = sum(max(-x, 0) for x in recent) / period

    if losses == 0:
        return 100.0
    return 100 - 100 / (1 + gains / losses)

def main():
    values, timestamp = index_data()
    fast = ema(values, 9)
    slow = ema(values, 21)
    strength = rsi(values)

    if fast[-1] > slow[-1] and values[-1] > values[-2] and 50 < strength < 70:
        signal = "BUY 🟢"
    elif fast[-1] < slow[-1] and values[-1] < values[-2] and 30 < strength < 50:
        signal = "SELL 🔴"
    else:
        signal = "TIDAK ADA SINYAL"

    next_time = datetime.fromtimestamp(
        int(timestamp) / 1000, timezone.utc
    ) + timedelta(minutes=5)

    local_time = next_time.astimezone(
        timezone(timedelta(hours=7))
    )

    message = (
        "🤖 BOT ACUAN CRYPTO IDX\n"
        f"Sinyal: {signal}\n"
        "Timeframe: M5\n"
        f"Waktu candle berikutnya: {local_time:%H:%M} WIB\n"
        f"EMA 9: {fast[-1]:.4f}\n"
        f"EMA 21: {slow[-1]:.4f}\n"
        f"RSI 14: {strength:.2f}\n"
        "Data OKX, simulasi 5 koin; bukan harga resmi Stockity."
    )

    send(message)

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("ERROR:", repr(error))
        try:
            send("⚠️ BOT ERROR: " + repr(error))
        finally:
            raise

        
