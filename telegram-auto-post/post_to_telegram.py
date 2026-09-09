#!/usr/bin/env python3
"""
Telegram kanalga har kuni avtomatik rasm+caption post qiluvchi skript.

Ishlash tartibi:
1. images/ papkasidagi barcha rasmlarni nomi bo'yicha alifbo tartibida saqlaydi
   (shuning uchun rasmlarni 01.jpg, 02.jpg, 03.jpg ... kabi nomlang - qaysi
   tartibda chiqishini shu nom belgilaydi)
2. state.json faylida "qaysi rasm navbatda" degan ma'lumot saqlanadi
3. Har ishga tushganda navbatdagi rasmni caption.txt dagi matn bilan kanalga yuboradi
4. Ro'yxat oxiriga yetganda (masalan 30-rasmdan keyin) yana boshiga qaytadi
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone

# ---- Sozlamalar (environment variables orqali keladi, GitHub Secrets'dan) ----
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # masalan: @mening_kanalim yoki -1001234567890

IMAGES_DIR = "images"
STATE_FILE = "state.json"
CAPTION_FILE = "caption.txt"

SUPPORTED_EXT = (".jpg", ".jpeg", ".png", ".webp")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"current_index": 0, "last_post_date": None, "cycle_count": 0}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_sorted_images():
    if not os.path.isdir(IMAGES_DIR):
        return []
    files = [
        f for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith(SUPPORTED_EXT)
    ]
    files.sort()  # 01.jpg, 02.jpg, ... tartibida
    return files


def load_caption():
    if os.path.exists(CAPTION_FILE):
        with open(CAPTION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def send_photo(image_path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as photo:
        resp = requests.post(
            url,
            data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"},
            files={"photo": photo},
            timeout=60,
        )
    return resp


def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("XATOLIK: BOT_TOKEN yoki CHANNEL_ID topilmadi (Secrets tekshiring).")
        sys.exit(1)

    images = get_sorted_images()
    if not images:
        print("images/ papkasida hech qanday rasm topilmadi. Post qo'yilmadi.")
        sys.exit(0)

    state = load_state()
    index = state.get("current_index", 0)

    # Agar rasmlar soni o'zgargan bo'lsa (ko'p/kam qilingan bo'lsa), indexni to'g'rilaymiz
    if index >= len(images):
        index = 0

    caption = load_caption()
    image_name = images[index]
    image_path = os.path.join(IMAGES_DIR, image_name)

    print(f"Yuborilyapti: {image_name} (index {index + 1}/{len(images)})")
    resp = send_photo(image_path, caption)

    if resp.status_code == 200 and resp.json().get("ok"):
        print("Muvaffaqiyatli yuborildi!")
        next_index = index + 1
        cycle_count = state.get("cycle_count", 0)
        if next_index >= len(images):
            next_index = 0
            cycle_count += 1
            print(f"Ro'yxat oxiriga yetdi -> {cycle_count}-marta boshidan qaytadi.")

        state["current_index"] = next_index
        state["cycle_count"] = cycle_count
        state["last_post_date"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
    else:
        print("XATOLIK: Telegramga yuborishda muammo bo'ldi.")
        print(resp.status_code, resp.text)
        sys.exit(1)


if __name__ == "__main__":
    main()
