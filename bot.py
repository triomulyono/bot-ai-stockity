

import os
import json
import subprocess
import requests
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

COINS = {
    "BTC-USDT": 0.50,
    "ETH-USDT": 0.20,
    "BNB-USDT": 0.10,
    "SOL-USDT": 0.10,
    "XRP-USDT": 0.10,
}

STATE_FILE = "signal_state.json"


def ambil_candle(symbol):
    url = "https://www.okx.com/api/v5/market/candles"
    r = requests.get(
        url,
        params={"instId": symbol, "bar": "5m", "limit": "100"},
        timeout=20,
    )
    r.raise_for_status()
    hasil = r.json()

    if hasil.get("code") != "0":
        raise ValueError(f"OKX gagal: {hasil}")

    candles = [c for c in hasil["data"] if c[8] == "1"]
    candles.sort(key=lambda c: int(c[0]))

    if len(candles) < 30:
        raise ValueError(f"Data candle {symbol} kurang")

    return candles


def buat_indeks():
    semua = {coin: ambil_candle(coin) for coin in COINS}

    waktu = set(c[0] for c in semua["BTC-USDT"])
    for data in semua.values():
        waktu &= set(c[0] for c in data)

    waktu = sorted(waktu, key=int)[-60:]

    if len(waktu) < 30:
        raise ValueError("Data waktu antar-koin tidak cocok")

    data_koin = {
        coin: {c[0]: c for c in data}
        for coin, data in semua.items()
    }

    nilai = []
    for ts in waktu:
        harga = sum(
            bobot * float(data_koin[coin][ts][4])
            for coin, bobot in COINS.items()
        )
        nilai.append(harga)

    return nilai, waktu[-1]


def ema(data, periode):
    k = 2 / (periode + 1)
    nilai = data[0]
    hasil = []

    for x in data:
        nilai = x * k + nilai * (1 - k)
        hasil.append(nilai)

    return hasil


def rsi(data, periode=14):
    perubahan = [
        data[i] - data[i - 1]
        for i in range(1, len(data))
    ]

    terakhir = perubahan[-periode:]
    naik = sum(max(x, 0) for x in terakhir) / periode
    turun = sum(max(-x, 0) for x in terakhir) / periode

    if turun == 0:
        return 100.0

    return 100 - (100 / (1 + naik / turun))


def baca_status():
    if not os.path.exists(STATE_FILE):
        return ""

    with open(STATE_FILE, "r") as f:
        return json.load(f).get("last_signal", "")


def simpan_status(sinyal):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_signal": sinyal}, f)

    subprocess.run(["git", "config", "user.name", "Bot AI Stockity"], check=True)
    subprocess.run(["git", "config", "user.email", "bot@github.com"], check=True)
    subprocess.run(["git", "add", STATE_FILE], check=True)

    perubahan = subprocess.run(
        ["git", "diff", "--cached", "--quiet"]
    )

    if perubahan.returncode == 1:
        subprocess.run(
            ["git", "commit", "-m", "Update signal state"],
            check=True,
        )
        subprocess.run(
            ["git", "push", "origin", "HEAD:main"],
            check=True,
        )


def kirim(pesan):
    if not TOKEN or not CHAT_ID:
        raise ValueError("Token Telegram atau CHAT_ID belum diatur")

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    r = requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": pesan},
        timeout=20,
    )
    r.raise_for_status()

    hasil = r.json()
    if not hasil.get("ok"):
        raise ValueError(f"Telegram gagal: {hasil}")


def main():
    data, ts = buat_indeks()

    e9 = ema(data, 9)
    e21 = ema(data, 21)
    nilai_rsi = rsi(data)

    if (
        e9[-1] > e21[-1]
        and data[-1] > data[-2]
        and 50 < nilai_rsi < 70
    ):
        sinyal = "BUY 🟢"

    elif (
        e9[-1] < e21[-1]
        and data[-1] < data[-2]
        and 30 < nilai_rsi < 50
    ):
        sinyal = "SELL 🔴"

    else:
        sinyal = "WAIT"

    sebelumnya = baca_status()

    if sinyal == sebelumnya:
        print(f"Tidak ada sinyal baru: {sinyal}")
        return

    if sinyal == "WAIT":
        print("WAIT: tidak mengirim pesan Telegram")
        simpan_status(sinyal)
        return

    waktu = datetime.fromtimestamp(
        int(ts) / 1000, timezone.utc
    ) + timedelta(minutes=5)

    waktu_wib = waktu.astimezone(
        timezone(timedelta(hours=7))
    )

    pesan = (
        "🤖 BOT ACUAN CRYPTO IDX\n"
        f"Sinyal: {sinyal}\n"
        "Timeframe: M5\n"
        f"Waktu candle berikutnya: {waktu_wib.strftime('%H:%M')} WIB\n"
        f"EMA 9: {e9[-1]:.4f}\n"
        f"EMA 21: {e21[-1]:.4f}\n"
        f"RSI 14: {nilai_rsi:.2f}\n"
        "Data OKX, simulasi 5 koin; bukan harga resmi Stockity."
    )

    kirim(pesan)
    simpan_status(sinyal)

    print("Sinyal baru berhasil dikirim:")
    print(pesan)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR BOT: {error}")
        raise
