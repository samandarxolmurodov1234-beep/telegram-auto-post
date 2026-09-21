#!/usr/bin/env python3
"""
Foydalanuvchi botga yuborgan rasmlarni tekshirib, OpenAI (gpt-image-1) orqali
professional tarzda qayta ishlaydi, sizga natijani qaytarib ko'rsatadi va
faqat siz "bo'ladi" deb javob berganingizda asosiy navbatga (images/) qo'shadi.

Agar OpenAI ishlamasa (billing, limit, xatolik), rasm ASL HOLIDA
(tuzatilmagan) saqlanadi va qaytariladi - jarayon to'xtamaydi.
"""

import os
import sys
import json
import base64
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

IMAGES_DIR = "images"
PENDING_DIR = "pending"
UPDATES_STATE_FILE = "updates_state.json"
PENDING_STATE_FILE = "pending_state.json"

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

OPENAI_EDIT_URL = "https://api.openai.com/v1/images/edits"

OPENAI_PROMPT = (
    "Create a photorealistic premium luxury jewelry advertising photograph "
    "using the uploaded reference image. REFERENCE JEWELRY — VERY IMPORTANT: "
    "Use the EXACT earrings and EXACT ring from the uploaded reference image. "
    "Do NOT redesign, regenerate, simplify, reshape, replace, or invent the "
    "jewelry. Preserve the exact: - jewelry design - shape - number of gold "
    "spheres - proportions - size - arrangement - faceted texture - gold "
    "color - surface details - structure - overall appearance. The earrings "
    "and ring must remain visually identical to the uploaded reference "
    "jewelry. Only improve the photography, lighting, environment, and "
    "atmosphere around them. SCENE: Place the exact reference earrings and "
    "ring elegantly on a premium white luxury jewelry display stand. A large "
    "rectangular padded white leather display panel mounted on a "
    "sophisticated white pedestal base. The display stand should look clean, "
    "expensive, minimal and professionally manufactured. COMPOSITION: Keep "
    "the same jewelry arrangement and placement as the reference image: - "
    "two matching vertical earrings positioned symmetrically in the upper "
    "left and upper right - matching ring positioned in the center-lower "
    "area - maintain natural spacing and proportions. ATMOSPHERE: High-end "
    "luxury jewelry brand advertising. Elegant premium jewelry showroom "
    "aesthetic. Minimalistic white luxury environment. Sophisticated, clean "
    "and expensive appearance. Soft warm ivory atmosphere mixed with pure "
    "white tones. Subtle luxurious glow surrounding the jewelry. LIGHTING: "
    "Professional luxury jewelry studio lighting. Large soft diffused key "
    "light from the front. Gentle side lighting. Subtle warm golden "
    "highlights reflecting naturally from the yellow gold. Beautiful "
    "controlled reflections on the faceted gold surfaces. Soft realistic "
    "contact shadows. Natural dimensionality. No harsh shadows. No black "
    "spots. No dirty gray areas. No excessive glare. BACKGROUND: Pure white "
    "seamless studio background. Very subtle warm-white gradient. Clean "
    "negative space. Soft premium glow. No visible wall corners. No "
    "horizon. No distracting objects. MATERIALS: The jewelry must look like "
    "real polished yellow gold. Preserve the exact faceted metal texture "
    "from the reference. Highly realistic metallic reflections. Realistic "
    "white leather texture on the display. Natural premium material "
    "appearance. CAMERA: Straight-on front-facing luxury product "
    "photography. Centered composition. Eye-level camera. 50mm professional "
    "product photography lens. Sharp focus on the jewelry. High "
    "micro-detail. Natural realistic perspective. FINAL STYLE: "
    "Ultra-photorealistic. High-end luxury jewelry campaign. Premium "
    "jewelry catalog photography. Elegant. Minimal. Sophisticated. Clean. "
    "Expensive. 8K quality. Realistic studio photography. ABSOLUTELY DO "
    "NOT: change the earrings, change the ring, redesign the jewelry, add "
    "or remove gold spheres, change proportions, change jewelry placement, "
    "add gemstones, add diamonds, change yellow gold to another metal, add "
    "extra jewelry, remove any jewelry, create different jewelry, add "
    "people, add hands, add text, add logos, add watermark, add decorative "
    "props, use a dark background, create black spots, create dirty "
    "surfaces, create artificial CGI-looking jewelry. The uploaded "
    "reference jewelry is the source of truth. The jewelry itself must "
    "remain unchanged. Only create a more luxurious, professional "
    "atmosphere, lighting, background and presentation around the exact "
    "reference jewelry."
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


def ai_enhance_photo(image_path):
    """
    OpenAI (gpt-image-1) orqali rasmni qayta ishlaydi. Agar ishlamasa
    (billing, limit, xatolik), asl rasm o'zgarishsiz qoladi.
    """
    if not OPENAI_API_KEY:
        print("Ogohlantirish: OPENAI_API_KEY topilmadi, asl rasm saqlanadi.")
        return

    try:
        with open(image_path, "rb") as img_file:
            files = {
                "image": (os.path.basename(image_path), img_file, "image/jpeg"),
            }
            data = {
                "model": "gpt-image-1",
                "prompt": OPENAI_PROMPT,
                "size": "1024x1024",
            }
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

            resp = requests.post(
                OPENAI_EDIT_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=120,
            )

        result = resp.json()

        if resp.status_code != 200:
            print(f"Ogohlantirish: OpenAI xatolik qaytardi ({resp.status_code}): {result}")
            return

        b64_data = result["data"][0].get("b64_json")
        if not b64_data:
            print("Ogohlantirish: OpenAI javobida rasm topilmadi, asl rasm saqlanadi.")
            return

        image_bytes = base64.b64decode(b64_data)
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        print("OpenAI (gpt-image-1) orqali tuzatildi.")

    except Exception as e:
        print(f"Ogohlantirish: OpenAI bilan ishlashda xatolik, asl rasm saqlanadi: {e}")


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
        ai_enhance_photo(save_path)

        review_msg_id = send_photo_for_review(
            chat_id,
            save_path,
            "Rasm shunday tuzatildi. Mos bo'lsa shu xabarga javob qilib "
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
