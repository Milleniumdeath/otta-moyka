import json
import time
from datetime import date

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

SYSTEM_PROMPT = (
    "Sen OTTA Moyka avto yuvish tizimining yordamchi sun'iy intellekt botisan. "
    "Sen quyidagi TO'RT mavzuda maslahat berasan:\n"
    "1. Avto yuvish (mashina yuvish usullari, kimyoviy vositalar, jihozlar, "
    "ichki/tashqi tozalash, polirovka, detailing, suv tejash va xizmat sifati).\n"
    "2. Moliya (shaxsiy va kichik biznes moliyasi, byudjet, daromad-xarajat, "
    "narx belgilash, foyda hisoblash, jamg'arma, soliq asoslari, "
    "moliyaviy rejalashtirish).\n"
    "3. Biznes (avto yuvish va xizmat ko'rsatish biznesini yuritish, "
    "mijozlarni jalb qilish va ushlab qolish, marketing va reklama, "
    "xodimlarni boshqarish, narx strategiyasi, raqobat, sifatni oshirish, "
    "operatsion samaradorlik va biznesni o'stirish).\n"
    "4. Shaxsiy yordamchi rejimi (FAQAT moyka konteksti uchun): bugun "
    "mashinani yuvdirish maqsadga muvofiqmi, ob-havo qanday, yomg'ir yog'ishi "
    "mumkinmi, qachon yuvishga eng yaxshi vaqt — bunday savollarga foydalanuvchi "
    "uchun qisqa va amaliy javob berasan. Agar tizim senga 'BUGUNGI OB-HAVO' "
    "kontekstini bersa — undan foydalan, qiymatlarni o'zingdan o'ylab topma. "
    "Agar ob-havo konteksti yo'q bo'lsa va savol shu haqida bo'lsa, ma'lumot "
    "yo'qligini halol ayt va umumiy maslahat ber (masalan: yomg'irdan keyin "
    "2-3 soat kutish, quyoshli kunda yuvish afzal va h.k.).\n"
    "5. Eslatma yaratish (ESLATMA: tizim alohida ishlaydi): foydalanuvchi "
    "\"eslat\", \"esimga sol\" deb sana bilan so'rasa, tizim avtomatik "
    "eslatma yozadi va sen chaqirilmaysan. Ammo foydalanuvchi qanday eslatma "
    "yaratish haqida so'rasa, tushuntir: \"Ertaga ob-havo quyoshli bo'lsa "
    "mashinani yuvdirishni eslat\" kabi gaplar bilan eslatma yaratishi "
    "mumkinligini ayt.\n\n"
    "Agar foydalanuvchi bu TO'RT mavzudan tashqarida (siyosat, tibbiyot, "
    "dasturlash, shaxsiy hayot detallari, umumiy savollar va h.k.) so'rasa, "
    "muloyimlik bilan rad et va faqat avto yuvish, moliya, biznes hamda "
    "moykaga aloqador shaxsiy yordamchi (ob-havo + yuvish qarori) bo'yicha "
    "yordam bera olishingni ayt. Javoblaringni doimo o'zbek tilida, qisqa, "
    "aniq va amaliy ber. Foydalanuvchini hech qachon noto'g'ri yo'naltirma."
)

# Shaxsiy yordamchi rejimi: ob-havo / yuvish qaroriga aloqador kalit so'zlar
WEATHER_KEYWORDS = (
    'ob-havo', 'ob havo', 'obhavo', 'havo qanday', 'havo qalay',
    "yomg'ir", "yomg'ur", 'yomgir', 'yog\'a', 'yog\'adi', 'yogadi',
    "yog'sa", "yog'masa",
    'yuvsam', 'yuvdirsam', "yuvsam bo'lad", 'yuvsa boladi',
    'bugun yuvish', "bugun yuvdir", "bugun yuvsa",
    'shamol', 'harorat', 'issiq', 'sovuq', 'quyoshli', 'bulutli',
    'yuvish vaqti', 'qachon yuvish', "qachon yuvsam",
)


def _wants_weather(message: str) -> bool:
    """Foydalanuvchi savoli ob-havo/yuvish qaroriga aloqadormi?"""
    if not message:
        return False
    low = message.lower()
    return any(k in low for k in WEATHER_KEYWORDS)


def _weather_context() -> str:
    """Bugungi ob-havo ma'lumotini AI uchun matn ko'rinishida qaytaradi.

    Mavjud bo'lmasa bo'sh string. fetch_weather kesh bilan ishlaydi, shuning
    uchun har chaqiriqda tashqi API ga so'rov ketmaydi.
    """
    try:
        from .models import WeatherCache
        from .weather import fetch_weather, WEATHER_CITY
    except Exception:
        return ''

    today = date.today()
    wc = WeatherCache.objects.filter(date=today).order_by('-fetched_at').first()
    if wc is None:
        try:
            wc = fetch_weather()
        except Exception:
            wc = None

    if not wc:
        return ''

    if wc.rain_probability >= 60:
        advice = "Yomg'ir ehtimoli yuqori — yuvishni keyinga qoldirish tavsiya etiladi."
    elif wc.rain_probability >= 30:
        advice = "Yomg'ir ehtimoli o'rtacha — risk bor, lekin yuvish mumkin."
    else:
        advice = "Yomg'ir ehtimoli past — yuvish uchun yaxshi kun."

    parts = [
        f"BUGUNGI OB-HAVO KONTEKSTI ({wc.city}, {wc.date.strftime('%d.%m.%Y')}):",
        f"- Yomg'ir ehtimoli: {wc.rain_probability}%",
    ]
    if wc.description:
        parts.append(f"- Tavsif: {wc.description}")
    parts.append(f"- Tizim tavsiyasi: {advice}")
    parts.append(
        "Ushbu ma'lumotdan foydalanib mijozga yuvish qarori bo'yicha qisqa va "
        "amaliy javob ber. Raqamlarni o'zingdan o'ylab topma."
    )
    return "\n".join(parts)


# ─── Eslatma (Reminder) intent — kalit so'zlar va sana/shart parsing ───
REMINDER_TRIGGER_WORDS = (
    'eslat', 'eslatib', 'esimga sol', 'esimga sal', 'esda tut',
    'esdan chiqarma', 'esdan chiqar', 'eslatma',
    'remind', 'eslatib qo\'y', 'eslatib qoy',
)

# "Ertaga", "indinga", "bugun" va h.k. → bugundan kun ofseti
DATE_OFFSETS = {
    'bugun':         0,
    'ertaga':        1,
    "erta'ga":       1,
    'ertaganga':     1,
    'indinga':       2,
    'indin':         2,
    'birovkun':      2,
    'birov kun':     2,
    'birinchi kun':  1,
    'keyingi kun':   1,
}

WEEKDAY_NAMES = {
    'dushanba':  0, 'seshanba':   1, 'chorshanba': 2,
    'payshanba': 3, 'juma':       4, 'shanba':     5, 'yakshanba':  6,
}


def _is_reminder_request(message: str) -> bool:
    """Foydalanuvchi yangi eslatma yaratmoqchimi?"""
    low = message.lower()
    return any(w in low for w in REMINDER_TRIGGER_WORDS)


def _parse_reminder(message: str):
    """Xabardan trigger_date va condition'ni topadi.

    Qaytaradi: (trigger_date, condition_code, title) yoki None.
    """
    from datetime import date, timedelta
    import re

    low = message.lower()
    today = date.today()
    trigger = None

    # 1) Kalit so'zlar — "ertaga", "indinga", "bugun"
    for word, offset in DATE_OFFSETS.items():
        if word in low:
            trigger = today + timedelta(days=offset)
            break

    # 2) "N kun(dan) keyin"
    if trigger is None:
        m = re.search(r"(\d{1,2})\s*kun(?:dan)?\s*key", low)
        if m:
            trigger = today + timedelta(days=int(m.group(1)))

    # 3) Hafta kuni — "juma kuni", "shanba"
    if trigger is None:
        for name, wd in WEEKDAY_NAMES.items():
            if name in low:
                delta = (wd - today.weekday()) % 7
                if delta == 0:
                    delta = 7
                trigger = today + timedelta(days=delta)
                break

    # 4) Aniq sana "DD.MM" yoki "DD.MM.YYYY"
    if trigger is None:
        m = re.search(r"(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?", message)
        if m:
            try:
                d, mo = int(m.group(1)), int(m.group(2))
                y = int(m.group(3)) if m.group(3) else today.year
                if y < 100: y += 2000
                trigger = date(y, mo, d)
                if trigger < today:  # o'tib ketgan — keyingi yilga
                    trigger = date(y + 1, mo, d)
            except (ValueError, TypeError):
                pass

    if trigger is None:
        return None  # sana topilmadi — bu ehtimol eslatma emas

    # Shart aniqlanishi
    condition = 'any'
    if any(w in low for w in ('quyoshli', 'ochiq havo', 'yaxshi havo')):
        condition = 'sunny'
    elif any(w in low for w in ("yomg'irsiz", "yomgirsiz", "yomg'ir bo'lmasa",
                                "yomg'ir yog'masa", "yomgir yogmasa")):
        condition = 'no_rain'

    # Sarlavha — foydalanuvchi xabaridan qisqartmasi
    title = message.strip()
    if len(title) > 100:
        title = title[:97] + '...'

    return trigger, condition, title


def _create_reminder_from_chat(user, message):
    """Eslatma yaratadi, agar parse muvaffaqiyatli bo'lsa Reminder obyektini qaytaradi."""
    parsed = _parse_reminder(message)
    if not parsed:
        return None
    trigger_date, condition, title = parsed
    from .models import Reminder
    return Reminder.objects.create(
        user=user,
        kind=Reminder.Kind.USER_REQUEST,
        trigger_date=trigger_date,
        condition=condition,
        title=title,
        message=message,
    )


# Bittasi band/limitda bo'lsa keyingisiga o'tiladi
FALLBACK_MODELS = [
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
    'gemini-2.0-flash',
]


def _candidate_models():
    models = []
    primary = (settings.GEMINI_MODEL or '').strip()
    if primary:
        models.append(primary)
    for m in FALLBACK_MODELS:
        if m not in models:
            models.append(m)
    return models


@login_required
@require_POST
def ai_chat(request):
    if not settings.GEMINI_API_KEY:
        return JsonResponse(
            {'error': "AI xizmati hozircha sozlanmagan. Administrator bilan bog'laning."},
            status=503,
        )

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': "So'rov noto'g'ri formatda."}, status=400)

    message = (payload.get('message') or '').strip()
    if not message:
        return JsonResponse({'error': 'Xabar bo\'sh bo\'lishi mumkin emas.'}, status=400)
    if len(message) > 2000:
        return JsonResponse({'error': 'Xabar juda uzun (maksimal 2000 belgi).'}, status=400)

    # ── Eslatma intent: agar foydalanuvchi yangi eslatma yaratmoqchi bo'lsa,
    # Gemini'ni chaqirmaymiz — to'g'ridan-to'g'ri DB'ga yozamiz va tasdiq qaytaramiz.
    if _is_reminder_request(message):
        reminder = _create_reminder_from_chat(request.user, message)
        if reminder:
            cond_label = {
                'any':     "shartsiz",
                'sunny':   "quyoshli havoda",
                'no_rain': "yomg'ir bo'lmasa",
            }.get(reminder.condition, "shartsiz")
            reply = (
                f"✅ Eslatma sozlandi!\n\n"
                f"📅 Sana: <b>{reminder.trigger_date.strftime('%d.%m.%Y')}</b>\n"
                f"☁️ Shart: {cond_label}\n"
                f"📨 O'sha kuni email orqali eslatma yuboramiz.\n\n"
                f"Eslatmalaringizni \"Eslatmalarim\" bo'limidan ko'rib chiqishingiz mumkin."
            )
            return JsonResponse({'reply': reply, 'reminder_id': reminder.id})
        # Sana topilmadi — Gemini'ga yo'naltirib aniqroq so'rashga ko'maklash
        return JsonResponse({
            'reply': (
                "Eslatma yaratish uchun aniq sana kerak. Masalan:\n"
                "• \"Ertaga ob-havo quyoshli bo'lsa mashinani yuvdirishni eslat\"\n"
                "• \"Juma kuni yuvishni eslatib qo'y\"\n"
                "• \"3 kundan keyin eslatma yarat\""
            )
        })

    # Oldingi suhbat tarixi (so'nggi 6 ta xabar)
    history = payload.get('history') or []
    contents = []
    for item in history[-6:]:
        role = 'user' if item.get('role') == 'user' else 'model'
        text = (item.get('text') or '').strip()[:2000]
        if text:
            contents.append({'role': role, 'parts': [{'text': text}]})
    contents.append({'role': 'user', 'parts': [{'text': message}]})

    # Shaxsiy yordamchi rejimi: ob-havo savoli bo'lsa, kontekstni inject qilamiz
    system_text = SYSTEM_PROMPT
    if _wants_weather(message):
        ctx = _weather_context()
        if ctx:
            system_text = SYSTEM_PROMPT + "\n\n" + ctx
        else:
            system_text = (
                SYSTEM_PROMPT
                + "\n\nESLATMA: Bugungi ob-havo ma'lumoti tizimda mavjud emas. "
                  "Mijozga buni halol ayt va umumiy maslahat ber (yomg'irdan "
                  "keyin 2-3 soat kutish, ob-havo ilovasini tekshirish va h.k.)."
            )

    request_body = {
        'system_instruction': {'parts': [{'text': system_text}]},
        'contents': contents,
        'generationConfig': {
            'temperature': 0.6,
            'maxOutputTokens': 800,
        },
    }

    last_status = None
    for model in _candidate_models():
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        for attempt in range(2):
            try:
                resp = requests.post(
                    url,
                    params={'key': settings.GEMINI_API_KEY},
                    json=request_body,
                    timeout=30,
                )
            except requests.RequestException:
                last_status = 'conn'
                break  # keyingi modelga o'tamiz

            if resp.status_code == 200:
                data = resp.json()
                try:
                    reply = data['candidates'][0]['content']['parts'][0]['text'].strip()
                except (KeyError, IndexError, TypeError):
                    return JsonResponse(
                        {'error': "AI javob bera olmadi. Savolni boshqacha bering."},
                        status=502,
                    )
                return JsonResponse({'reply': reply})

            last_status = resp.status_code
            # 503 — vaqtinchalik band, bir marta qayta urinib ko'ramiz
            if resp.status_code == 503 and attempt == 0:
                time.sleep(1.2)
                continue
            # 429/404/boshqa — shu modelda davom etmaymiz, keyingisiga
            break

    if last_status == 429:
        msg = "AI xizmati so'rovlar limitiga yetdi. Bir necha daqiqadan so'ng urinib ko'ring."
    elif last_status == 503:
        msg = "AI xizmati hozir juda band. Iltimos, biroz kutib qayta urinib ko'ring."
    elif last_status == 'conn':
        msg = "AI xizmatiga ulanib bo'lmadi. Internet aloqasini tekshiring."
    else:
        msg = "AI xizmatida xatolik yuz berdi. Keyinroq urinib ko'ring."
    return JsonResponse({'error': msg}, status=502)
