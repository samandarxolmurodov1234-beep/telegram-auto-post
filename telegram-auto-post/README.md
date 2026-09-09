# Telegram kanalga avtomatik post qo'yish (GitHub Actions)

## Bu tizim qanday ishlaydi

1. **Rasm qabul qilish**: Siz botga (`@avto_post_jewerly_bot`) rasm yuborasiz.
   GitHub Actions har 10 daqiqada tekshirib, yangi rasmlarni avtomatik
   `images/` papkasiga saqlab boradi (navbat tartibida: 001.jpg, 002.jpg, ...)
   va sizga "✅ Rasm navbatga qo'shildi" deb tasdiq yuboradi.
2. **Kunlik post**: Har kuni belgilangan vaqtda (masalan 08:00) navbatdagi
   birinchi rasm, sizning caption matningiz bilan kanalga avtomatik yuboriladi.
3. **Aylanma tsikl**: Rasmlar ro'yxati tugagach (masalan 30-rasmdan keyin),
   tizim yana 1-rasmdan boshlab davom etadi.

Faqat **sizning** Telegram hisobingizdan (`1110328463`) kelgan rasmlar qabul
qilinadi — boshqa hech kim botga rasm tashlab, navbatga aralasha olmaydi.

## 1-qadam: GitHub'da repository yaratish

1. https://github.com ga kiring (akkaunt yo'q bo'lsa, ro'yxatdan o'ting — bepul)
2. Yuqori o'ngdagi **+** → **New repository**
3. Nomini kiriting, masalan `telegram-auto-post`
4. **Private** qilib qo'ying (rasmlaringiz va sozlamalar ochiq bo'lmasin)
5. **Create repository**

## 2-qadam: Fayllarni yuklash

Berilgan barcha fayl va papkalarni (`post_to_telegram.py`,
`receive_images.py`, `caption.txt`, `state.json`, `updates_state.json`,
`.github/` papkasi, `images/` papkasi) o'sha repository ichiga yuklang:

- **Add file → Upload files** → fayllarni sudrab tashlang → **Commit changes**

> ⚠️ `.github/workflows/` papkasi ichidagi ikkala `.yml` fayl ham albatta
> o'sha joyda, o'zgarishsiz qolishi kerak.

## 3-qadam: Botni qayta xavfsiz qilish

Avval yuborgan tokeningizni **darhol bekor qiling**:
1. Telegram'da **@BotFather** → `/mybots` → `@avto_post_jewerly_bot`
2. **API Token** → **Revoke current token**
3. Yangi tokenni saqlab qo'ying (keyingi qadamda kerak bo'ladi)

## 4-qadam: Secrets qo'shish

Repository → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**. Uchta Secret qo'shasiz:

| Nomi | Qiymati |
|---|---|
| `BOT_TOKEN` | Yangi (revoke qilingandan keyingi) bot tokeningiz |
| `CHANNEL_ID` | Kanalingiz (masalan `@kanal_nomi` yoki raqamli ID) |
| `ALLOWED_USER_ID` | `1110328463` |

## 5-qadam: Caption matni

`caption.txt` fayli allaqachon sizning matningiz bilan tayyor:
```
📲 @Gold2004m
📞 +998 90 688 61 66

Bizning manzil
@MM_Gold1
```
Keyinchalik o'zgartirmoqchi bo'lsangiz, shu faylni GitHub'da tahrirlab,
saqlashingiz kifoya — keyingi barcha postlarda yangi matn ishlatiladi.

## 6-qadam: Botga rasm yuborish

Endi Telegram'da botingizga (`@avto_post_jewerly_bot`) shunchaki rasmlarni
birma-bir yuboring (yoki bir nechtasini birdan). 10 daqiqa ichida ular
avtomatik `images/` papkasiga tushadi va sizga tasdiq xabari keladi.

Tezroq sinab ko'rmoqchi bo'lsangiz: **Actions** → **Receive Images From Bot**
→ **Run workflow** — darhol tekshiradi, kutish shart emas.

## 7-qadam: Kunlik post vaqtini sozlash

`.github/workflows/daily-post.yml` faylidagi bu qator har kuni soat 08:00
(Toshkent vaqti) da post qo'yishni bildiradi:
```yaml
- cron: "0 3 * * *"
```
Boshqa vaqt kerak bo'lsa ayting, hisoblab to'g'ri qatorni beraman (UTC
bo'yicha yozilishi kerak).

## 8-qadam: Sinab ko'rish

Kamida bitta rasm `images/` papkasiga tushgandan keyin:
1. **Actions** → **Daily Telegram Post** → **Run workflow**
2. Bir necha soniyadan so'ng kanalingizga rasm + caption tushadi

Xatolik chiqsa, o'sha workflow'ning logini ochib, matnini menga yuboring —
birga tuzatamiz.

## Keyinchalik ishlatish

- **Yangi rasm qo'shish**: botga shunchaki rasm tashlang, tizim o'zi navbatga
  qo'yadi — hech narsani qo'lda sozlash shart emas
- **Caption o'zgartirish**: `caption.txt` faylini tahrirlang
- **Postlash vaqtini o'zgartirish**: `daily-post.yml` dagi cron qatorini
  o'zgartiring (yoki ayting, men yangilab beraman)
