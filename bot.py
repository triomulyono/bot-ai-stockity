

import os
import requests
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

COINS = {
    "BTC-USDT": 0.50,
    "ETH-USDT": 0.20,
    "BNB-USDT": 0.10,
    "SOL-USDT": 0.10,
    "XRP-USDT": 0.10
}

def kirim(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": pesan
    }, timeout=20).raise_for_status()

def ambil_candle(symbol):
    url = "https://www.okx.com/api/v5/market/candles"
    r = requests.get(url, params={
        "instId": symbol,
        "bar": "5m",
        "limit": "100"
    }, timeout=20)
    r.raise_for_status()
    hasil = r.json()

    if hasil.get("code") != "0":
        raise ValueError(str(hasil))

    candles = [
        x for x in hasil["data"]
        if x[8] == "1"
    ]
    candles.sort(key=lambda x: int(x[0]))

    if len(candles) < 30:
        raise ValueError("Data candle kurang")

    return candles

def buat_indeks():
    semua = {coin: ambil_candle(coin) for coin in COINS}

    waktu = set(x[0] for x in semua["BTC-USDT"])
    for data in semua.values():
        waktu &= set(x[0] for x in data)

    waktu = sorted(waktu, key=int)[-60:]

    if len(waktu) < 30:
        raise ValueError("Data waktu koin tidak cocok")

    hasil = []
    for ts in waktu:
        nilai = 0
        for coin, bobot in COINS.items():
            data = {x[0]: x for x in semua[coin]}
            nilai += bobot * float(data[ts][4])
        hasil.append(nilai)

    return hasil, waktu[-1]

def ema(data, periode):
    k = 2 / (periode + 1)
    nilai = data[0]
    hasil = []
    for x in data:
        nilai = x * k + nilai * (1-k)
        hasil.append(nilai)
    return hasil

def rsi(data, periode=14):
    perubahan = [data[i]-data[i-1] for i in range(1,len(data))]
    naik = sum(max(x,0) for x in perubahan[-periode:])/periode
    turun = sum(max(-x,0) for x in perubahan[-periode:])/periode
    if turun == 0:
        return 100
    return 100-(100/(1+naik/turun))

if __name__ == "__main__":
    try:
        data, ts = buat_indeks()
        e9 = ema(data, 9)
        e21 = ema(data, 21)
        nilai_rsi = rsi(data)

        bullish = (
            e9[-1] > e21[-1]
            and data[-1] > data[-2]
            and nilai_rsi > 50
            and nilai_rsi < 70
        )

        bearish = (
            e9[-1] < e21[-1]
            and data[-1] < data[-2]
            and nilai_rsi < 50
            and nilai_rsi > 30
        )

        if bullish or bearish:
            sinyal = "BUY 🟢" if bullish else "SELL 🔴"

            waktu = datetime.fromtimestamp(
                int(ts)/1000,
                timezone.utc
            ) + timedelta(minutes=5)

            waktu_lokal = waktu.astimezone(
                timezone(timedelta(hours=7))
            )

            kirim(
                "🤖 SINYAL ACUAN CRYPTO IDX\n"
                f"Sinyal: {sinyal}\n"
                "Timeframe: M5\n"
                f"Waktu entry: {waktu_lokal.strftime('%H:%M')} WIB\n"
                f"EMA 9: {e9[-1]:.4f}\n"
                f"EMA 21: {e21[-1]:.4f}\n"
                f"RSI 14: {nilai_rsi:.2f}\n"
                "Data: OKX, indeks simulasi 5 koin\n"
                "Bukan harga resmi Stockity."
            )

    except Exception as e:
        kirim("⚠️ ERROR BOT: " + str(e))
        raise
