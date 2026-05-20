import requests
from datetime import date
from django.conf import settings
from .models import WeatherCache

OPENWEATHER_API_KEY = getattr(settings, 'OPENWEATHER_API_KEY', '')
WEATHER_CITY = getattr(settings, 'WEATHER_CITY', 'Oltiariq')

def fetch_weather(city=None):
    """Bugungi ob-havoni OpenWeatherMap dan olib, bazaga yozadi."""
    if not OPENWEATHER_API_KEY:
        return None

    city = city or WEATHER_CITY
    today = date.today()

    # Agar bugungi kesh mavjud bo'lsa, qaytaramiz
    cached = WeatherCache.objects.filter(city=city, date=today).first()
    if cached:
        return cached

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': city,
        'appid': OPENWEATHER_API_KEY,
        'units': 'metric',
        'lang': 'uz'
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if resp.status_code == 200:
            rain = data.get('rain', {})
            # OpenWeatherMap "rain" maydoni mm/soat, biz ehtimoliyatni foizga aylantiramiz
            # Oddiy hisob: agar "rain" maydoni mavjud bo'lsa, ehtimollik 80% deb olamiz,
            # yoki "pop" (probability of precipitation) mavjud emas, shuning uchun
            # bulut qoplamiga qarab baholaymiz.
            clouds = data.get('clouds', {}).get('all', 0)
            # Bulut qoplami bo'yicha taxminiy ehtimollik: bulut 100% -> 80%, 0% -> 5%
            probability = int(5 + clouds * 0.75) if not rain else 80
            description = data['weather'][0]['description'] if data.get('weather') else ''
            wc, _ = WeatherCache.objects.update_or_create(
                city=city, date=today,
                defaults={
                    'rain_probability': probability,
                    'description': description
                }
            )
            return wc
    except Exception:
        # API ulanishda xatolik bo'lsa, eski keshdan foydalanish yoki None
        return cached  # cached None bo'lishi mumkin
    return None