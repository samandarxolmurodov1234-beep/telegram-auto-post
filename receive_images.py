#!/usr/bin/env python3
"""
Foydalanuvchi botga yuborgan rasmlarni tekshirib, Gemini AI orqali rang
tuzatish qilib, images/ papkasiga ketma-ket raqamlab saqlaydigan skript.
"""

import os
import sys
import json
import base64
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

IMAGES_DIR = "images"
UPDATES_STATE_FILE = "updates_state.json"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

GEMINI_MODEL = "gemini-2.5-flash-image"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

GEMINI_PROMPT = (
    "Apply only automatic white balance, exposure and contrast correction "
    "to this product photo. Do not change the actual color/hue of the "
    "jewelry item itself (gold must stay gold, silver must stay silver). "
    "Do not add, remove, or redraw any objects or details. Keep the exact "
    "same composition, angle and framing. Only clean up the lighting and "
    "make the background look neutral and clean."
)


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


def gemini_color_correct(image_path):
    """
    Rasmni Gemini AI orqali rang/yorug'lik tuzatishdan o'tkazadi.
    Muvaffaqiyatsiz bo'lsa, asl rasm o'zgarishsiz qoladi.
    """
    if not GEMINI_API_KEY:
        print("Ogohlantirish: GEMINI_API_KEY topilmadi, rang tuzatish o'tkazib yuborildi.")
        return

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                    {"text": GEMINI_PROMPT},
                ]
            }],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }

        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
            timeout=90,
        )
        data = resp.json()

        if resp.status_code != 200:
            print(f"Ogohlantirish: Gemini API xatolik qaytardi ({resp.status_code}): {data}")
            return

        parts = data["candidates"][0]["content"]["parts"]
        for part in parts:
            if "inline_data" in part or "inlineData" in part:
                inline = part.get("inline_data") or part.get("inlineData")
                new_bytes = base64.b64decode(inline["data"])
                with open(image_path, "wb") as f:
                    f.write(new_bytes)
                print("Gemini orqali rang tuzatildi.")
                return

        print("Ogohlantirish: Gemini javobida rasm topilmadi, asl rasm saqlanadi.")

    except Exception as e:
        print(f"Ogohlantirish: Gemini bilan ishlashda xatolik, asl rasm saqlanadi: {e}")


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
            continue

        best_photo = photos[-1]
        file_id = best_photo["file_id"]

        number = get_next_image_number()
        filename = f"{number:03d}.jpg"
        save_path = os.path.join(IMAGES_DIR, filename)

        try:
            download_file(file_id, save_path)
            gemini_color_correct(save_path)
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
