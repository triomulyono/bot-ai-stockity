import requests
import time

TOKEN = 8818767645:AAEGZXmWTDunODjYhW9cbU-v1YejJIbbO_k
CHAT_ID = 7053873075

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

pesan = "BOT AI STOCKITY AKTIF!"

while True:
    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": pesan
        })
        print("Pesan terkirim")
    except Exception as e:
        print(e)

    time.sleep(300)
