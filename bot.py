

import os
import json
import requests
import subprocess
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

STATE_FILE = "state.json"

def send(message):
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": message},
        timeout=20
    )
    r.raise_for_status()

def get_candles(symbol):
    r = requests.get(
        "https://www.okx.com/api/v5/market/candles",
        params={"instId": symbol, "bar": "5m", "limit": "100"},
        timeout=20
    )
    r.raise_for_status()
    result = r.json()

    if result.get("code") != "0":
        raise RuntimeError(str(result))

    rows = [x for x in result["data"] if x[8] == "1"]
    rows.sort(key=lambda x: int(x[0]))

    if len(rows) < 30:
        raise RuntimeError("Data candle kurang: " + symbol)

    return {x[0]: x for x in rows}

def make_index():
    all_data = {s: get_candles(s) for s in COINS}
    common = set.intersection(
        *(set(v.keys()) for v in all_data.values())
    )
    times = sorted(common, key=int)[-60:]

    if len(times) < 30:
        raise RuntimeError("Data candle tidak cocok")

    first = times[0]
    values = []

    for t in times:
        value = 0
        for symbol, weight in COINS.items():
            base = float(all_data[symbol][first][4])
            close = float(all_data[symbol][t][4])
            value += weight * (close / base) * 100
        values.append(value)

    return values, times[-1]

def ema(values, period):
    alpha = 2 / (period + 1)
    result = [values[0]]

    for value in values[1:]:
        result.append(
            alpha * value + (1 - alpha) * result[-1]
        )

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
        return 100

    return 100 - 100 / (1 + gains / losses)

def save_state(candle):
    state = {"last_candle": candle}

    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

    subprocess.run(
        ["git", "config", "user.name", "Stockity Bot"],
        check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "bot@users.noreply.github.com"],
        check=True
    )
    subprocess.run(["git", "add", STATE_FILE], check=True)

    check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"]
    )

    if check.returncode == 1:
        subprocess.run(
            ["git", "commit", "-m", "Update last signal candle"],
            check=True
        )
        subprocess.run(["git", "push"], check=True)

def main():
    values, candle = make_index()

    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
    else:
        state = {"last_candle": ""}

    if state.get("last_candle") == candle:
        print("Candle sudah diproses. Tidak mengirim ulang.")
        return

    fast = ema(values, 9)
    slow = ema(values, 21)
    strength = rsi(values)

    if (
        fast[-1] > slow[-1]
        and values[-1] > values[-2]
        and 50 < strength < 70
    ):
        signal = "BUY 🟢"
    elif (
        fast[-1] < slow[-1]
        and values[-1] < values[-2]
        and 30 < strength < 50
    ):
        signal = "SELL 🔴"
    else:
        signal = None

    # Simpan candle walaupun tidak ada sinyal
    save_state(candle)

    if signal:
        next_time = datetime.fromtimestamp(
            int(candle) / 1000,
            timezone.utc
        ) + timedelta(minutes=5)

        local_time = next_time.astimezone(
            timezone(timedelta(hours=7))
        )

        send(
            "🤖 SINYAL ACUAN CRYPTO IDX\n"
            f"Sinyal: {signal}\n"
            "Timeframe: M5\n"
            f"Waktu candle berikutnya: {local_time:%H:%M} WIB\n"
            f"EMA 9: {fast[-1]:.4f}\n"
            f"EMA 21: {slow[-1]:.4f}\n"
            f"RSI 14: {strength:.2f}\n"
            "Acuan simulasi 5 koin OKX, bukan harga resmi Stockity."
        )

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("ERROR:", repr(error))
        raise

        
