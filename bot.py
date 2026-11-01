
import os
import requests
import time
import math

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

COINS = {
    "BTCUSDT": 0.50,
    "ETHUSDT": 0.20,
    "BNBUSDT": 0.10,
    "SOLUSDT": 0.10,
    "XRPUSDT": 0.10
}

def ambil_data(symbol):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "5m", "limit": 100}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def buat_indeks():
    data = {}
    for coin in COINS:
        data[coin] = ambil_data(coin)

    hasil = []
    for i in range(100):
        nilai = 0
        for coin, bobot in COINS.items():
            harga_awal = float(data[coin][0][4])
            harga = float(data[coin][i][4])
            nilai += bobot * (harga / harga_awal) * 100
        hasil.append(nilai)
    return hasil

def ema(data, periode):
    hasil = []
    k = 2 / (periode + 1)
    nilai = data[0]
    for harga in data:
        nilai = harga * k + nilai * (1 - k)
        hasil.append(nilai)
    return hasil

def rsi(data, periode=14):
    perubahan = [data[i] - data[i-1] for i in range(1, len(data))]
    naik = sum(max(x, 0) for x in perubahan[-periode:]) / periode
    turun = sum(max(-x, 0) for x in perubahan[-periode:]) / periode
    if turun == 0:
        return 100
    return 100 - (100 / (1 + naik / turun))

def kirim(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": pesan
    }, timeout=15).raise_for_status()

if __name__ == "__main__":
    try:
        indeks = buat_indeks()
        e9 = ema(indeks, 9)
        e21 = ema(indeks, 21)
        nilai_rsi = rsi(indeks)

        if e9[-1] > e21[-1] and indeks[-1] > indeks[-2] and nilai_rsi < 70:
            sinyal = "BUY 🟢"
        elif e9[-1] < e21[-1] and indeks[-1] < indeks[-2] and nilai_rsi > 30:
            sinyal = "SELL 🔴"
        else:
            sinyal = "WAIT ⏳"

        pesan = (
            "🤖 BOT AI CRYPTO IDX (SIMULASI)\n"
            "Timeframe: M5\n"
            f"Sinyal: {sinyal}\n"
            f"EMA 9: {e9[-1]:.4f}\n"
            f"EMA 21: {e21[-1]:.4f}\n"
            f"RSI 14: {nilai_rsi:.2f}\n"
            "Acuan: BTC, ETH, BNB, SOL, XRP\n"
            "Catatan: bukan harga resmi Stockity."
        )
        kirim(pesan)

    except Exception as e:
        kirim("⚠️ Bot gagal mengambil data: " + str(e))
