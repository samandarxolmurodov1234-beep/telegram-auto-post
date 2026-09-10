#!/usr/bin/env python3
"""
Foydalanuvchi botga yuborgan rasmlarni tekshirib, Gemini AI orqali rang
tuzatadi, sizga natijani qaytarib ko'rsatadi va faqat siz "bo'ladi" deb
javob berganingizda asosiy navbatga (images/) qo'shadi.

Ishlash tartibi:
1. Rasm keladi -> Gemini orqali tuzatiladi -> pending/ papkasiga saqlanadi
   -> sizga tuzatilgan rasm qaytarib yuboriladi, "bo'ladi" deb javob
   berishingiz so'raladi
2. Siz o'sha xabarga javob qilib "bo'ladi" (yoki "ha", "ok") desangiz ->
   rasm images/ papkasiga ko'chiriladi, navbatga qo'shiladi
3. Siz "yo'q" desangiz -> rasm bekor qilinadi, navbatga qo'shilmaydi
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
PENDING_DIR = "pending"
UPDATES_STATE_FILE = "updates_state.json"
PENDING_STATE_FILE = "pending_state.json"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

GEMINI_MODEL = "gemini-2.5-flash-image"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

GEMINI_PROMPT = (
    "Enhance this product photograph of a gold jewelry piece for e-commerce use. "
    "Clean up the white textured jewelry display stand so it looks pristine, "
    "spotless, and completely free of any stains, marks, pen lines, or metal "
    "clips. Make the background and display surface perfectly smooth and clean. "
    "Apply soft, professional studio-quality lighting with sharp focus on the "
    "jewelry item's detailed textures. "
    "IMPORTANT: Do not change the actual color, shape, size, design, or any "
    "detail of the jewelry item itself - it must remain exactly as in the "
    "original photo. Only clean the display stand/background and improve the "
    "lighting quality."
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


def gemini_color_correct(image_path):
    """Muvaffaqiyatsiz bo'lsa, asl rasm o'zgarishsiz qoladi."""
    if not GEMINI_API_KEY:
        print("Ogohlantirish: GEMINI_API_KEY topilmadi, tuzatish o'tkazib yuborildi.")
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
            print(f"Ogohlantirish: Gemini xatolik qaytardi ({resp.status_code}):
