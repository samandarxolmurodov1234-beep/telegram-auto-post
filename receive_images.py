#!/usr/bin/env python3
"""
Foydalanuvchi botga yuborgan rasmlarni tekshirib, Gemini AI orqali rang
tuzatadi (agar limit tugagan bo'lsa - bepul algoritmik usulga avtomatik
o'tadi), sizga natijani qaytarib ko'rsatadi va faqat siz "bo'ladi" deb
javob berganingizda asosiy navbatga (images/) qo'shadi.

Ishlash tartibi:
1. Rasm keladi -> avval Gemini orqali tuzatishga harakat qilinadi;
   agar Gemini ishlamasa (limit, xatolik) -> bepul algoritmik usulga
   avtomatik o'tiladi -> pending/ papkasiga saqlanadi
2. Sizga tuzatilgan rasm qaytarib yuboriladi, "bo'ladi" deb javob
   berishingiz so'raladi
3. Siz o'sha xabarga javob qilib "bo'ladi" (yoki "ha", "ok") desangiz ->
   rasm images/ papkasiga ko'chiriladi, navbatga qo'shiladi
4. Siz "yo'q" desangiz -> rasm bekor qilinadi, navbatga qo'shilmaydi
"""

import os
import sys
import json
import base64
import requests
from PIL import Image, ImageOps

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

IMAGES_DIR = "images"
PENDING_DIR = "pending"
UPDATES_STATE_FILE = "updates_state.json"
PENDING_STATE_FILE = "pending_state.json"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

GEMINI_MODEL = "gemini-2.5-flash-image"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

GEMINI_PROMPT = (
    "Mutlaqo toza va top-toza oq teksturali zargarlik stendida joylashgan "
    "oltin uzukning professional mahsulot fotosurati. Stend yuzasida hech "
    "qanday dog'lar, ruchka izlari yoki metall qisqichlar yo'q. Barcha "
    "keraksiz dog'lar olib tashlangan, orqa fon va stend mutlaqo toza va "
    "professional ko'rinishda. "
    "MUHIM: uzukning o'zi - uning rangi, shakli, o'lchami, dizayni va "
    "har qanday detali - asl rasmdagidek qoladi, hech qanday o'zgarish "
    "kiritilmaydi. Faqat stend/fon tozalanadi va yorug'lik yaxshilanadi."
)

CONFIRM_WORDS = {"bo'ladi", "boladi", "ha", "ok", "okay", "tasdiqlayman"}
REJECT_WORDS = {"yo'q", "yoq", "yo'q.", "bekor"}


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def get_next_number(folder):
    ensure_dir(folder)
    existing = [
        f for f in os.listdir(folder)
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


def algorithmic_color_correct(image_path):
    """Bepul, algoritmik rang/kontrast tuzatish (zaxira usul)."""
    try:
        img = Image.open(image_path).convert("RGB")
        corrected = ImageOps.autocontrast(img, cutoff=1)
        corrected.save(image_path, "JPEG", quality=95)
        print("Bepul algoritmik usul bilan tuzatildi.")
    except Exception as e:
        print(f"Ogohlantirish: algoritmik tuzatish ham ishlamadi: {e}")


def gemini_color_correct(image_path):
    """
    Avval Gemini AI orqali tuzatishga harakat qiladi. Agar Gemini limiti
    tugagan yoki xatolik bo'lsa, avtomatik bepul algoritmik usulga o'tadi.
    """
    if not GEMINI_API_KEY:
        print("Ogohlantirish: GEMINI_API_KEY topilmadi, bepul usulga o'tildi.")
        algorithmic_color_correct(image_path)
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

        resp = requests.post(f"{GEMINI_URL}?key={GEMINI_API_KEY}", json=payload, timeout=90)
        data = resp.json()

        if resp.status_code != 200:
            print(f"Ogohlantirish: Gemini xatolik qaytardi ({resp.status_code}), bepul usulga o'tildi.")
            algorithmic_color_correct(image_path)
            return

        parts = data["candidates"][0]["content"]["parts"]
        for part in parts:
            inline = part.get("inline_data") or part.get("inlineData")
            if inline:
                new_bytes = base64.b64decode(inline["data"])
                with open(image_path, "wb") as f:
                    f.write(new_bytes)
                print("Gemini orqali tuzatildi.")
                return

        print("Ogohlantirish: Gemini javobida rasm topilmadi, bepul usulga o'tildi.")
        algorithmic_color_correct(image_path)

    except Exception as e:
        print(f"Ogohlantirish: Gemini bilan ishlashda xatolik, bepul usulga o'tildi: {e}")
        algorithmic_color_correct(image_path)


def send_message(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", data={"chat_id": chat_id, "text": text}, timeout=30)


def send_photo_for_review(chat_id, image_path, caption):
    url = f"{API_URL}/sendPhoto"
    with open(image_path, "rb") as photo:
        resp = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": photo},
            timeout=60,
        )
    data = resp.json()
    if data.get("ok"):
        return data["result"]["message_id"]
    return None


def handle_new_photo(message, pending_state):
    photos = message.get("photo")
    if not photos:
        return

    chat_id = message["chat"]["id"]
    best_photo = photos[-1]
    file_id = best_photo["file_id"]

    ensure_dir(PENDING_DIR)
    number = get_next_number(PENDING_DIR)
    filename = f"{number:03d}.jpg"
    save_path = os.path.join(PENDING_DIR, filename)

    try:
        download_file(file_id, save_path)
        gemini_color_correct(save_path)

        review_msg_id = send_photo_for_review(
            chat_id,
            save_path,
            "Rangi shunday tuzatildi. Mos bo'lsa shu xabarga javob qilib "
            "\"bo'ladi\" deb yozing, mos bo'lmasa \"yo'q\" deb yozing."
        )

        if review_msg_id:
            pending_state[str(review_msg_id)] = {"file": save_path, "chat_id": chat_id}
        else:
            send_message(chat_id, "❌ Rasmni qaytarib yuborishda xatolik yuz berdi.")

    except Exception as e:
        print(f"XATOLIK rasmni qayta ishlashda: {e}")
        send_message(chat_id, "❌ Rasmni qayta ishlashda xatolik yuz berdi.")


def handle_text_reply(message, pending_state):
    text = (message.get("text") or "").strip().lower()
    reply_to = message.get("reply_to_message")
    if not reply_to:
        return

    reply_id = str(reply_to.get("message_id"))
    if reply_id not in pending_state:
        return

    entry = pending_state[reply_id]
    chat_id = entry["chat_id"]
    pending_path = entry["file"]

    if text in CONFIRM_WORDS:
        if os.path.exists(pending_path):
            ensure_dir(IMAGES_DIR)
            number = get_next_number(IMAGES_DIR)
            final_filename = f"{number:03d}.jpg"
            final_path = os.path.join(IMAGES_DIR, final_filename)
            os.rename(pending_path, final_path)
            send_message(chat_id, f"✅ Rasm navbatga qo'shildi ({final_filename})")
        else:
            send_message(chat_id, "❌ Rasm topilmadi, qaytadan yuboring.")
        del pending_state[reply_id]

    elif text in REJECT_WORDS:
        if os.path.exists(pending_path):
            os.remove(pending_path)
        send_message(chat_id, "🗑 Rasm bekor qilindi, navbatga qo'shilmadi.")
        del pending_state[reply_id]

    else:
        send_message(chat_id, "Iltimos \"bo'ladi\" yoki \"yo'q\" deb javob bering.")


def main():
    if not BOT_TOKEN or not ALLOWED_USER_ID:
        print("XATOLIK: BOT_TOKEN yoki ALLOWED_USER_ID topilmadi.")
        sys.exit(1)

    updates_state = load_json(UPDATES_STATE_FILE, {"last_update_id": 0})
    pending_state = load_json(PENDING_STATE_FILE, {})

    offset = updates_state.get("last_update_id", 0) + 1
    resp = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 5}, timeout=30)
    data = resp.json()

    if not data.get("ok"):
        print("XATOLIK: getUpdates ishlamadi:", data)
        sys.exit(1)

    updates = data["result"]
    if not updates:
        print("Yangi xabar yo'q.")
        return

    max_update_id = updates_state.get("last_update_id", 0)

    for update in updates:
        max_update_id = max(max_update_id, update["update_id"])
        message = update.get("message")
        if not message:
            continue

        sender_id = str(message.get("from", {}).get("id", ""))
        if sender_id != str(ALLOWED_USER_ID):
            print(f"E'tibor berilmadi: ruxsatsiz foydalanuvchi ({sender_id}).")
            continue

        if message.get("photo"):
            handle_new_photo(message, pending_state)
        elif message.get("text") and message.get("reply_to_message"):
            handle_text_reply(message, pending_state)

    updates_state["last_update_id"] = max_update_id
    save_json(UPDATES_STATE_FILE, updates_state)
    save_json(PENDING_STATE_FILE, pending_state)


if __name__ == "__main__":
    main()
