import json
import time

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

SYSTEM_PROMPT = (
    "Sen OTTA Moyka avto yuvish tizimining yordamchi sun'iy intellekt botisan. "
    "Sen quyidagi UCH mavzuda maslahat berasan:\n"
    "1. Avto yuvish (mashina yuvish usullari, kimyoviy vositalar, jihozlar, "
    "ichki/tashqi tozalash, polirovka, detailing, suv tejash va xizmat sifati).\n"
    "2. Moliya (shaxsiy va kichik biznes moliyasi, byudjet, daromad-xarajat, "
    "narx belgilash, foyda hisoblash, jamg'arma, soliq asoslari, "
    "moliyaviy rejalashtirish).\n"
    "3. Biznes (avto yuvish va xizmat ko'rsatish biznesini yuritish, "
    "mijozlarni jalb qilish va ushlab qolish, marketing va reklama, "
    "xodimlarni boshqarish, narx strategiyasi, raqobat, sifatni oshirish, "
    "operatsion samaradorlik va biznesni o'stirish).\n\n"
    "Agar foydalanuvchi bu uch mavzudan tashqarida (siyosat, tibbiyot, "
    "dasturlash, shaxsiy hayot, umumiy savollar va h.k.) so'rasa, muloyimlik "
    "bilan rad et va faqat avto yuvish, moliya hamda biznes bo'yicha yordam "
    "bera olishingni ayt. Javoblaringni doimo o'zbek tilida, qisqa, aniq va "
    "amaliy ber. Foydalanuvchini hech qachon noto'g'ri yo'naltirma."
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

    # Oldingi suhbat tarixi (so'nggi 6 ta xabar)
    history = payload.get('history') or []
    contents = []
    for item in history[-6:]:
        role = 'user' if item.get('role') == 'user' else 'model'
        text = (item.get('text') or '').strip()[:2000]
        if text:
            contents.append({'role': role, 'parts': [{'text': text}]})
    contents.append({'role': 'user', 'parts': [{'text': message}]})

    request_body = {
        'system_instruction': {'parts': [{'text': SYSTEM_PROMPT}]},
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
