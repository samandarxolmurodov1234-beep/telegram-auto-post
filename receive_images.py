#!/usr/bin/env python3
"""
Foydalanuvchi botga yuborgan rasmlarni tekshirib, images/ papkasiga
ketma-ket raqamlab saqlaydigan skript.

Ishlash tartibi:
1. Telegram'dan getUpdates orqali yangi xabarlarni oladi
   (faqat oxirgi safar to'xtagan joydan keyingi yangilarini - offset orqali)
2. Faqat ALLOWED_USER_ID dan kelgan va rasm (photo) bo'lgan xabarlarni qabul qiladi
3. Har bir rasmni eng yuqori sifatda yuklab oladi va images/ papkasiga
   navbatdagi raqam bilan saqlaydi (masalan mavjudi 07 bo'lsa, keyingisi 08.jpg)
4. Foydalanuvchiga "qabul qilindi" deb tasdiq xabar yuboradi
5. updates_state.json faylida oxirgi ko'rilgan update_id'ni saqlab qo'yadi
   (shu bilan bir xil rasm ikki marta qabul qilinmaydi)
"""

import os
import sys
import json
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID")  # faqat shu ID'dan rasm qabul qilinadi

IMAGES_DIR = "images"
UPDATES_STATE_FILE = "updates_state.json"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def load_updates_state():
    if os.path.exists(UPDATES_STATE_FILE):
        with open(UPDATES_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_update_id": 0}


def save_updates_state(state):
    with open(UPDATES_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_next_image_number():
    if not os.path.isdir(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
    existing = [
        f for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    ]
    numbers = []
    for f in existing:
        name = os.path.splitext(f)[0]
        if name.isdigit():
            numbers.append(int(name))
    return (max(numbers) + 1) if numbers else 1


def download_file(file_id, save_path):
    file_info = requests.get(f"{API_URL}/getFile", params={"file_id": file_id}, timeout=30).json()
    file_path = file_info["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    resp = requests.get(file_url, timeout=60)
    with open(save_path, "wb") as f:
        f.write(resp.content)


def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", data={"chat_id": chat_id, "text": text}, timeout=30)


def main():
    if not BOT_TOKEN or not ALLOWED_USER_ID:
        print("XATOLIK: BOT_TOKEN yoki ALLOWED_USER_ID topilmadi (Secrets tekshiring).")
        sys.exit(1)

    state = load_updates_state()
    offset = state.get("last_update_id", 0) + 1

    resp = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 5}, timeout=30)
    data = resp.json()

    if not data.get("ok"):
        print("XATOLIK: getUpdates ishlamadi:", data)
        sys.exit(1)

    updates = data["result"]
    if not updates:
        print("Yangi xabar yo'q.")
        return

    saved_count = 0
    max_update_id = state.get("last_update_id", 0)

    for update in updates:
        max_update_id = max(max_update_id, update["update_id"])
        message = update.get("message")
        if not message:
            continue

        sender_id = str(message.get("from", {}).get("id", ""))
        if sender_id != str(ALLOWED_USER_ID):
            print(f"E'tibor berilmadi: ruxsatsiz foydalanuvchidan xabar ({sender_id}).")
            continue

        photos = message.get("photo")
        if not photos:
            continue  # rasm bo'lmagan xabarlarni e'tiborsiz qoldiramiz

        # Telegram bir nechta o'lchamda yuboradi, oxirgisi (eng kattasi) tanlanadi
        best_photo = photos[-1]
        file_id = best_photo["file_id"]

        number = get_next_image_number()
        filename = f"{number:03d}.jpg"
        save_path = os.path.join(IMAGES_DIR, filename)

        try:
            download_file(file_id, save_path)
            saved_count += 1
            print(f"Saqlandi: {filename}")
            send_message(message["chat"]["id"], f"✅ Rasm navbatga qo'shildi ({filename})")
        except Exception as e:
            print(f"XATOLIK rasmni saqlashda: {e}")
            send_message(message["chat"]["id"], "❌ Rasmni saqlashda xatolik yuz berdi.")

    state["last_update_id"] = max_update_id
    save_updates_state(state)
    print(f"Jami {saved_count} ta yangi rasm saqlandi.")


if __name__ == "__main__":
    main()
