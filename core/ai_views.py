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


# ════════════════════════════════════════════════════════════════
# LABORATORIYA — Kimyoviy formula generatsiyasi (Moyka egasi uchun)
# ════════════════════════════════════════════════════════════════

LAB_SYSTEM_PROMPT = (
    "Sen tajribali kimyogarsan va avto-yuvish (carwash) detailing sanoati "
    "uchun professional kimyoviy aralashmalarni ishlab chiqasan. "
    "Vazifang — moyka egasiga maxsus mahsulot tayyorlash uchun aniq formula "
    "berish.\n\n"
    "MUHIM QOIDALAR:\n"
    "1. Faqat o'zbek tilida javob qaytar.\n"
    "2. Faqat JSON formatda javob ber, JSON'dan tashqari matn yozma.\n"
    "3. Komponentlarni umumiy, sotuvga mavjud kimyoviy moddalar nomi bilan ber "
    "(masalan: \"natriy lauril sulfat (SLS)\", \"izopropil spirti\", \"distillangan suv\").\n"
    "4. Miqdorlarni aniq son va o'lchov birligi bilan ber (gramm, litr, ml, %).\n"
    "5. Foiz nisbati JAMI 100% bo'lishi shart bo'lgan formulalarda buni tekshir.\n"
    "6. Xavfsizlik bo'limida MUHIM ogohlantirishlarni keltir: qo'lqop, niqob, "
    "ventilyatsiya, aralashtirish tartibi (xavfli reaksiyalarni oldini olish), "
    "saqlash va bolalardan uzoq tutish.\n"
    "7. Tayyorlash bosqichlarini raqamlangan ko'rinishda, ketma-ket ber.\n"
    "8. Agar foydalanuvchi xohishi tijoriy/o'q-otish/zaharli mahsulot bo'lsa, "
    "rad et va sababini tushuntir (xavfsizlik bo'limida).\n\n"
    "JSON FORMAT (qat'iy):\n"
    "{\n"
    '  "name": "Formula nomi (qisqa, 3-6 so\'z)",\n'
    '  "yield_volume": "Tayyor mahsulot hajmi, masalan 5 litr",\n'
    '  "ingredients": [\n'
    '    {"name": "Komponent nomi", "amount": "Miqdor", "role": "Vazifasi"}\n'
    '  ],\n'
    '  "instructions": ["1. Birinchi bosqich...", "2. Ikkinchi bosqich..."],\n'
    '  "safety_notes": ["Xavfsizlik 1", "Xavfsizlik 2"],\n'
    '  "usage_notes": ["Qo\'llash maslahati 1", "..."]\n'
    "}"
)

CATEGORY_LABELS = {
    'shampoo':   "avtomobil tashqi yuvish shampuni",
    'foam':      "avtomobil uchun faol ko'pik (foam shampoo)",
    'wax':       "avtomobil mumi (wax / sealant)",
    'polish':    "avtomobil polirovka pastasi",
    'interior':  "avtomobil saloni tozalovchi",
    'glass':     "avtomobil shisha tozalovchi",
    'tire':      "avtomobil shinasi/rezina parlatuvchi",
    'degreaser': "avtomobil dvigatel/yog' ketkazuvchi (degreaser)",
    'plastic':   "plastik va rezinani tiklovchi",
    'disinfect': "salon uchun dezinfeksiyalovchi vosita",
    'other':     "avto-detailing kimyoviy aralashmasi",
}


def _parse_lab_response(text: str):
    """AI javobidan JSON'ni ajratib oladi (markdown bloklarda yashirilgan bo'lsa ham)."""
    import re
    text = (text or '').strip()
    if not text:
        raise ValueError("empty text")

    # 1) ```json ... ``` markdown blokini olib tashlash
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        text = m.group(1)
    else:
        # 2) Birinchi { dan oxirgi } gacha ajratib olamiz
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            text = text[start:end + 1]

    # Ba'zan AI trailing comma qo'yadi — to'g'rilashga harakat qilamiz
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Trailing comma'ni olib tashlash
        cleaned = re.sub(r",(\s*[}\]])", r"\1", text)
        return json.loads(cleaned)


@login_required
@require_POST
def lab_generate(request):
    """Owner uchun: AI yordamida kimyoviy aralashma formulasini generatsiya qiladi."""
    if not getattr(request.user, 'is_owner', False):
        return JsonResponse({'error': "Ruxsat yo'q."}, status=403)

    if not settings.GEMINI_API_KEY:
        return JsonResponse(
            {'error': "AI xizmati hozircha sozlanmagan. Administrator bilan bog'laning."},
            status=503,
        )

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': "So'rov noto'g'ri formatda."}, status=400)

    category = (payload.get('category') or '').strip().lower()
    if category not in CATEGORY_LABELS:
        return JsonResponse({'error': "Noto'g'ri turi tanlandi."}, status=400)

    purpose = (payload.get('purpose') or '').strip()
    if not purpose or len(purpose) < 10:
        return JsonResponse({'error': "Maqsadni batafsilroq yozing (kamida 10 belgi)."}, status=400)
    if len(purpose) > 1500:
        return JsonResponse({'error': "Maqsad juda uzun (max 1500 belgi)."}, status=400)

    yield_volume = (payload.get('yield_volume') or '').strip()[:60]
    constraints = (payload.get('constraints') or '').strip()[:600]

    user_prompt_parts = [
        f"Mahsulot turi: {CATEGORY_LABELS[category]}.",
        f"Vazifa va talab: {purpose}",
    ]
    if yield_volume:
        user_prompt_parts.append(f"Maqsadli hosil hajmi: {yield_volume}.")
    if constraints:
        user_prompt_parts.append(f"Qo'shimcha shartlar va cheklovlar: {constraints}")
    user_prompt_parts.append(
        "Yuqoridagi talablar asosida JSON formatda professional formulani yarat."
    )
    user_prompt = "\n".join(user_prompt_parts)

    request_body = {
        'system_instruction': {'parts': [{'text': LAB_SYSTEM_PROMPT}]},
        'contents': [{'role': 'user', 'parts': [{'text': user_prompt}]}],
        'generationConfig': {
            'temperature': 0.5,
            'maxOutputTokens': 2048,
            'responseMimeType': 'application/json',
        },
        'safetySettings': [
            {'category': 'HARM_CATEGORY_HARASSMENT',        'threshold': 'BLOCK_ONLY_HIGH'},
            {'category': 'HARM_CATEGORY_HATE_SPEECH',       'threshold': 'BLOCK_ONLY_HIGH'},
            {'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'threshold': 'BLOCK_ONLY_HIGH'},
            {'category': 'HARM_CATEGORY_DANGEROUS_CONTENT', 'threshold': 'BLOCK_ONLY_HIGH'},
        ],
    }

    last_status = None
    last_detail = ''
    used_model = ''
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
                    timeout=60,
                )
            except requests.RequestException as e:
                last_status = 'conn'
                last_detail = str(e)[:200]
                break

            if resp.status_code == 200:
                data = resp.json()

                # Safety blockini tekshirish
                prompt_feedback = data.get('promptFeedback') or {}
                if prompt_feedback.get('blockReason'):
                    return JsonResponse({
                        'error': "AI xavfsizlik filtri so'rovni bloklab qo'ydi. "
                                 "Maqsadni boshqacha so'zlar bilan ifodalang.",
                    }, status=502)

                candidates = data.get('candidates') or []
                if not candidates:
                    last_status = 'empty'
                    last_detail = 'no candidates'
                    break

                finish_reason = candidates[0].get('finishReason', '')
                if finish_reason == 'SAFETY':
                    return JsonResponse({
                        'error': "AI xavfsizlik filtri tomonidan bloklandi. "
                                 "Boshqa so'zlar bilan urinib ko'ring.",
                    }, status=502)

                try:
                    raw_text = candidates[0]['content']['parts'][0]['text']
                except (KeyError, IndexError, TypeError):
                    last_status = 'empty'
                    last_detail = f'no text, finish={finish_reason}'
                    break

                if not raw_text or not raw_text.strip():
                    last_status = 'empty'
                    last_detail = f'empty text, finish={finish_reason}'
                    break

                try:
                    parsed = _parse_lab_response(raw_text)
                except (json.JSONDecodeError, ValueError):
                    # Bir marta keyingi modelga o'tib ko'ramiz
                    last_status = 'parse'
                    last_detail = raw_text[:200]
                    break

                # Minimal struktura tekshiruvi
                if not isinstance(parsed, dict) or not parsed.get('ingredients'):
                    last_status = 'parse'
                    last_detail = 'no ingredients in parsed'
                    break

                used_model = model
                return JsonResponse({
                    'recipe': parsed,
                    'category': category,
                    'ai_model': used_model,
                })

            # 200 emas
            last_status = resp.status_code
            try:
                err_data = resp.json()
                last_detail = (err_data.get('error') or {}).get('message', '')[:200]
            except Exception:
                last_detail = resp.text[:200] if resp.text else ''

            if resp.status_code == 503 and attempt == 0:
                time.sleep(1.5)
                continue
            break

    if last_status == 429:
        msg = "AI xizmati so'rovlar limitiga yetdi. Bir necha daqiqadan so'ng urinib ko'ring."
    elif last_status == 503:
        msg = "AI xizmati hozir juda band. Iltimos, biroz kutib qayta urinib ko'ring."
    elif last_status == 'conn':
        msg = f"AI xizmatiga ulanib bo'lmadi. Internet aloqasini tekshiring. ({last_detail})"
    elif last_status == 'parse':
        msg = "AI tushunarli formatda javob bermadi. Qaytadan urinib ko'ring yoki maqsadni boshqacha yozing."
    elif last_status == 'empty':
        msg = "AI bo'sh javob qaytardi. Maqsadni batafsilroq yozib qayta urinib ko'ring."
    elif last_status == 400:
        reason = last_detail or "sabab noma'lum"
        msg = f"So'rov noto'g'ri tuzilgan: {reason}"
    else:
        msg = f"AI xizmatida xatolik yuz berdi. Keyinroq urinib ko'ring. ({last_status}: {last_detail})"
    return JsonResponse({'error': msg}, status=502)
