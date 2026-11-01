
import os
import requests

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

COINS = {
    "bitcoin": 0.50,
    "ethereum": 0.20,
    "binancecoin": 0.10,
    "solana": 0.10,
    "ripple": 0.10
}

def kirim(pesan):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": pesan
    }, timeout=20).raise_for_status()

def ambil_harga():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(COINS.keys()),
        "price_change_percentage": "1h"
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    hasil = {}
    for coin in data:
        hasil[coin["id"]] = coin["price_change_percentage_1h_in_currency"]

    if len(hasil) != 5 or any(v is None for v in hasil.values()):
        raise ValueError("Data lima koin belum lengkap")

    return hasil

if __name__ == "__main__":
    try:
        harga = ambil_harga()
        perubahan = sum(
            harga[coin] * bobot
            for coin, bobot in COINS.items()
        )

        if perubahan > 0.10:
            sinyal = "BUY 🟢"
        elif perubahan < -0.10:
            sinyal = "SELL 🔴"
        else:
            sinyal = "WAIT ⏳"

        pesan = (
            "🤖 BOT ACUAN CRYPTO IDX\n"
            "Sinyal: " + sinyal + "\n"
            f"Perubahan indeks 1 jam: {perubahan:.3f}%\n"
            "Acuan: BTC 50%, ETH 20%, BNB 10%, SOL 10%, XRP 10%\n"
            "Data: CoinGecko\n"
            "Catatan: bukan harga resmi Stockity dan bukan sinyal M5."
        )
        kirim(pesan)

    except Exception as e:
        try:
            kirim("⚠️ Gagal mengambil data CoinGecko: " + str(e))
        except Exception:
            pass
        raise
