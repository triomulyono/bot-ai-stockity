
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
    "XRP-USDT": 0.10,
}


def kirim(pesan):
    if not TOKEN or not CHAT_ID:
        raise ValueError(
            "TELEGRAM_TOKEN atau CHAT_ID belum diatur di GitHub Secrets"
        )

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": pesan},
        timeout=20,
    )
    response.raise_for_status()

    hasil = response.json()
    if not hasil.get("ok"):
        raise ValueError(f"Telegram gagal mengirim: {hasil}")


def ambil_candle(symbol):
    url = "https://www.okx.com/api/v5/market/candles"
    response = requests.get(
        url,
        params={"instId": symbol, "bar": "5m", "limit": "100"},
        timeout=20,
    )
    response.raise_for_status()
    hasil = response.json()

    if hasil.get("code") != "0":
        raise ValueError(f"OKX gagal untuk {symbol}: {hasil}")

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

    nilai_indeks = []
    for ts in waktu:
        nilai = sum(
            bobot * float(data_koin[coin][ts][4])
            for coin, bobot in COINS.items()
        )
        nilai_indeks.append(nilai)

    return nilai_indeks, waktu[-1]


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


def main():
    data, ts = buat_indeks()

    e9 = ema(data, 9)
    e21 = ema(data, 21)
    nilai_rsi = rsi(data)

    bullish = (
        e9[-1] > e21[-1]
        and data[-1] > data[-2]
        and 50 < nilai_rsi < 70
    )

    bearish = (
        e9[-1] < e21[-1]
        and data[-1] < data[-2]
        and 30 < nilai_rsi < 50
    )

    if bullish:
        sinyal = "BUY 🟢"
    elif bearish:
        sinyal = "SELL 🔴"
    else:
        sinyal = "BELUM ADA SINYAL"

    waktu_candle = datetime.fromtimestamp(
        int(ts) / 1000, timezone.utc
    ) + timedelta(minutes=5)

    waktu_lokal = waktu_candle.astimezone(
        timezone(timedelta(hours=7))
    )

    pesan = (
        "🤖 BOT ACUAN CRYPTO IDX\n"
        f"Sinyal: {sinyal}\n"
        "Timeframe: M5\n"
        f"Waktu candle berikutnya: {waktu_lokal.strftime('%H:%M')} WIB\n"
        f"EMA 9: {e9[-1]:.4f}\n"
        f"EMA 21: {e21[-1]:.4f}\n"
        f"RSI 14: {nilai_rsi:.2f}\n"
        "Data OKX, simulasi 5 koin; bukan harga resmi Stockity."
    )

    kirim(pesan)
    print("Pesan berhasil dikirim ke Telegram:")
    print(pesan)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR BOT: {error}")
        raise
