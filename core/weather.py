import requests
from datetime import date
from django.conf import settings
from .models import WeatherCache

OPENWEATHER_API_KEY = getattr(settings, 'OPENWEATHER_API_KEY', '')
WEATHER_CITY = getattr(settings, 'WEATHER_CITY', 'Oltiariq')

# Open-Meteo (kalitsiz) uchun mashhur shaharlar koordinatalari fallback.
# Geocoding API ham ishlatamiz, lekin tarmoq bo'lmasa shu yerdan olamiz.
FALLBACK_COORDS = {
    'oltiariq':   (40.3690, 71.0440),
    'farg\'ona':  (40.3864, 71.7864),
    'fargona':    (40.3864, 71.7864),
    'fergana':    (40.3864, 71.7864),
    'toshkent':   (41.2995, 69.2401),
    'tashkent':   (41.2995, 69.2401),
    'samarqand':  (39.6542, 66.9597),
    'samarkand':  (39.6542, 66.9597),
    'buxoro':     (39.7681, 64.4556),
    'bukhara':    (39.7681, 64.4556),
    'andijon':    (40.7821, 72.3442),
    'andijan':    (40.7821, 72.3442),
    'namangan':   (40.9983, 71.6726),
    'qo\'qon':    (40.5283, 70.9425),
    'qoqon':      (40.5283, 70.9425),
    'kokand':     (40.5283, 70.9425),
    'marg\'ilon': (40.4711, 71.7242),
    'margilon':   (40.4711, 71.7242),
}

WMO_CODE_UZ = {
    0:  'ochiq quyoshli',
    1:  'asosan ochiq',
    2:  'qisman bulutli',
    3:  'bulutli',
    45: 'tumanli',
    48: 'qirovli tuman',
    51: 'yengil shivalama',
    53: 'o\'rta shivalama',
    55: 'kuchli shivalama',
    61: 'yengil yomg\'ir',
    63: 'o\'rta yomg\'ir',
    65: 'kuchli yomg\'ir',
    66: 'muzli yomg\'ir',
    67: 'kuchli muzli yomg\'ir',
    71: 'yengil qor',
    73: 'o\'rta qor',
    75: 'kuchli qor',
    77: 'qor donachalari',
    80: 'qisqa yomg\'ir yog\'ishi',
    81: 'o\'rta yomg\'ir yog\'ishi',
    82: 'kuchli yomg\'ir yog\'ishi',
    85: 'qor yog\'ishi',
    86: 'kuchli qor yog\'ishi',
    95: 'momoqaldiroq',
    96: 'do\'l bilan momoqaldiroq',
    99: 'kuchli do\'lli momoqaldiroq',
}


def _geocode_city(city):
    """Open-Meteo geocoding yoki fallback ro'yxatdan koordinata."""
    key = city.lower().strip()
    if key in FALLBACK_COORDS:
        return FALLBACK_COORDS[key]
    try:
        resp = requests.get(
            'https://geocoding-api.open-meteo.com/v1/search',
            params={'name': city, 'count': 1, 'language': 'uz'},
            timeout=5,
        )
        data = resp.json()
        results = data.get('results') or []
        if results:
            return (results[0]['latitude'], results[0]['longitude'])
    except Exception:
        pass
    return FALLBACK_COORDS.get('oltiariq')  # eng oxirgi himoya


def _fetch_open_meteo(city):
    """Open-Meteo'dan (kalitsiz) bugungi yomg'ir ehtimoli va tavsifini oladi."""
    coords = _geocode_city(city)
    if not coords:
        return None
    lat, lon = coords
    try:
        resp = requests.get(
            'https://api.open-meteo.com/v1/forecast',
            params={
                'latitude': lat,
                'longitude': lon,
                'current': 'temperature_2m,weather_code',
                'daily': 'precipitation_probability_max,weather_code,temperature_2m_max,temperature_2m_min',
                'timezone': 'auto',
                'forecast_days': 1,
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception:
        return None

    daily = data.get('daily') or {}
    current = data.get('current') or {}
    pops = daily.get('precipitation_probability_max') or []
    codes = daily.get('weather_code') or []
    t_max = (daily.get('temperature_2m_max') or [None])[0]
    t_min = (daily.get('temperature_2m_min') or [None])[0]

    probability = int(pops[0]) if pops and pops[0] is not None else 0
    code = codes[0] if codes else current.get('weather_code', 0)
    desc = WMO_CODE_UZ.get(int(code), '')

    parts = []
    if desc:
        parts.append(desc)
    if t_max is not None and t_min is not None:
        parts.append(f"{round(t_min)}°…{round(t_max)}°C")
    elif current.get('temperature_2m') is not None:
        parts.append(f"{round(current['temperature_2m'])}°C")
    description = ', '.join(parts)

    return {'probability': probability, 'description': description}


def _fetch_openweather(city):
    """OpenWeatherMap (kalitli) — agar OPENWEATHER_API_KEY bo'lsa."""
    if not OPENWEATHER_API_KEY:
        return None
    try:
        resp = requests.get(
            'https://api.openweathermap.org/data/2.5/weather',
            params={'q': city, 'appid': OPENWEATHER_API_KEY,
                    'units': 'metric', 'lang': 'uz'},
            timeout=5,
        )
        data = resp.json()
        if resp.status_code != 200:
            return None
    except Exception:
        return None

    rain = data.get('rain', {})
    clouds = data.get('clouds', {}).get('all', 0)
    probability = int(5 + clouds * 0.75) if not rain else 80
    description = data['weather'][0]['description'] if data.get('weather') else ''
    return {'probability': probability, 'description': description}


def fetch_weather(city=None, force=False):
    """Bugungi ob-havoni olib bazaga yozadi.

    Avval kesh; keyin OpenWeatherMap (agar kalit bo'lsa); keyin Open-Meteo
    (kalitsiz) — shu tartibda urinadi. `force=True` da keshdan o'tib o'tadi.
    """
    city = city or WEATHER_CITY
    today = date.today()

    if not force:
        cached = WeatherCache.objects.filter(city=city, date=today).first()
        if cached:
            return cached

    data = _fetch_openweather(city) or _fetch_open_meteo(city)
    if not data:
        return WeatherCache.objects.filter(city=city, date=today).first()

    wc, _ = WeatherCache.objects.update_or_create(
        city=city, date=today,
        defaults={
            'rain_probability': data['probability'],
            'description':      data['description'],
        }
    )
    return wc