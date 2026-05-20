from django.core.management.base import BaseCommand
from core.weather import fetch_weather

class Command(BaseCommand):
    help = "Bugungi ob-havoni OpenWeatherMap dan olib, bazaga yozadi"

    def handle(self, *args, **options):
        w = fetch_weather()
        if w:
            self.stdout.write(f"Ob-havo saqlandi: {w.city} {w.date}, yomg'ir ehtimoli {w.rain_probability}%")
        else:
            self.stdout.write("Ob-havo ma'lumoti olinmadi")