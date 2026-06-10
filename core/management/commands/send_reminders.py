"""Kunlik eslatmalarni jo'natuvchi komanda.

Ishlash logikasi:
1. Bugungi sanada turgan PENDING eslatmalarni topadi.
2. Har biri uchun shartni tekshiradi (ob-havoga qarab "sunny"/"no_rain" filtri).
3. Shart bajarilsa — email yuboradi, status='sent'.
4. Shart bajarilmasa — status='skipped'.
5. So'ng 7+ kun buyurtma bermagan mijozlarni topib, ularga avtomatik
   "mashinangizni yuvdirish vaqti keldi" eslatmasini yuboradi (cooldown 7 kun).

Cron / scheduler:
    python manage.py send_reminders
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Max

from accounts.models import User
from core.models import Reminder, Order
from core.weather import fetch_weather


def _weather_today():
    """Bugungi ob-havoni keshdan yoki Open-Meteo'dan oladi (rain_probability, description)."""
    try:
        wc = fetch_weather()
    except Exception:
        wc = None
    return wc


def _condition_satisfied(condition: str, weather) -> bool:
    """Eslatma sharti bugungi ob-havoda bajarilganmi."""
    if condition == Reminder.Condition.ANY:
        return True
    if weather is None:
        # ma'lumot yo'q — ehtiyot bo'lib eslatmani yuborib qo'yamiz
        return True
    p = weather.rain_probability or 0
    if condition == Reminder.Condition.SUNNY:
        return p < 30
    if condition == Reminder.Condition.NO_RAIN:
        return p < 50
    return True


def _send_email(user, subject, body):
    """Foydalanuvchiga email yuboradi. False bo'lsa, log qoldiriladi."""
    if not user.email:
        return False
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        return False


def _send_user_reminders(stdout):
    today = timezone.localdate()
    weather = _weather_today()

    qs = Reminder.objects.filter(
        kind=Reminder.Kind.USER_REQUEST,
        status=Reminder.Status.PENDING,
        trigger_date__lte=today,
    ).select_related('user')

    sent, skipped = 0, 0
    for rem in qs:
        if not _condition_satisfied(rem.condition, weather):
            rem.status = Reminder.Status.SKIPPED
            rem.save(update_fields=['status'])
            skipped += 1
            stdout.write(f"  -- Skipped #{rem.id} (shart bajarilmadi) — {rem.user}")
            continue

        weather_line = ""
        if weather:
            weather_line = (
                f"\n\nBugungi ob-havo ({weather.city}): "
                f"{weather.description or '—'}, "
                f"yomg'ir ehtimoli {weather.rain_probability}%."
            )

        body = (
            f"Assalomu alaykum, {rem.user.get_full_name() or rem.user.email}!\n\n"
            f"Siz so'ragan eslatma: {rem.title}{weather_line}\n\n"
            f"OTTA Avtomoyka ilovasi orqali buyurtma berishingiz mumkin."
        )

        ok = _send_email(rem.user, "OTTA — Yuvish eslatmasi", body)
        if ok:
            rem.status = Reminder.Status.SENT
            rem.sent_at = timezone.now()
            rem.save(update_fields=['status', 'sent_at'])
            sent += 1
            stdout.write(f"  OK Sent  #{rem.id} -> {rem.user.email}")
        else:
            stdout.write(f"  XX Email yuborilmadi #{rem.id} -> {rem.user}")

    return sent, skipped


def _send_inactive_reminders(stdout):
    """7+ kun buyurtma qilmagan mijozlarga avtomatik eslatma jo'natadi."""
    today = timezone.localdate()
    threshold_date = today - timedelta(days=Reminder.INACTIVE_THRESHOLD_DAYS)
    cooldown_date  = today - timedelta(days=Reminder.INACTIVE_COOLDOWN_DAYS)

    customers = (
        User.objects
        .filter(role=User.Role.CUSTOMER, is_active=True)
        .exclude(email='')
        .annotate(last_order=Max('customer_orders__created_at'))
    )

    sent = 0
    for c in customers:
        # 1) Hech qachon buyurtma qilmagan yoki oxirgi buyurtma 7+ kun oldin
        if c.last_order and c.last_order.date() > threshold_date:
            continue  # yaqinda buyurtma qilgan
        if c.last_order is None:
            # ro'yxatdan o'tgan, lekin hech qachon buyurtma qilmagan
            # 7+ kun ro'yxatda bo'lsa eslatish mumkin
            if c.date_joined.date() > threshold_date:
                continue

        # 2) Cooldown — oxirgi 7 kun ichida avto-eslatma yuborilgan bo'lmasin
        recent = Reminder.objects.filter(
            user=c,
            kind=Reminder.Kind.AUTO_INACTIVE,
            sent_at__gte=timezone.now() - timedelta(days=Reminder.INACTIVE_COOLDOWN_DAYS),
        ).exists()
        if recent:
            continue

        body = (
            f"Assalomu alaykum, {c.get_full_name() or c.email}!\n\n"
            f"Bir haftadan beri mashinangizni yuvdirmadingiz. "
            f"Mashinangizni yuvdirish vaqti keldi!\n\n"
            f"OTTA Avtomoyka ilovasiga kiring va o'zingizga qulay vaqtga "
            f"buyurtma bering.\n\n"
            f"Yangi mijozlarga maxsus aksiyalar mavjud — ko'rib chiqing!\n\n"
            f"Tashrifingiz uchun rahmat."
        )
        ok = _send_email(
            c,
            "OTTA — Mashinangizni yuvdirish vaqti keldi!",
            body,
        )
        if not ok:
            continue

        Reminder.objects.create(
            user=c,
            kind=Reminder.Kind.AUTO_INACTIVE,
            trigger_date=today,
            condition=Reminder.Condition.ANY,
            title="Mashinangizni yuvdirish vaqti keldi!",
            message=body,
            status=Reminder.Status.SENT,
            sent_at=timezone.now(),
        )
        sent += 1
        stdout.write(f"  OK Auto-inactive -> {c.email}")

    return sent


class Command(BaseCommand):
    help = "Eslatmalarni jo'natadi: foydalanuvchi so'rovlari + 7+ kun faolsiz mijozlar."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=== send_reminders ==="))

        self.stdout.write("\n[1/2] Foydalanuvchi eslatmalari...")
        sent_u, skipped_u = _send_user_reminders(self.stdout)
        self.stdout.write(self.style.SUCCESS(
            f"  -> Yuborildi: {sent_u}, o'tkazib yuborildi: {skipped_u}"
        ))

        self.stdout.write("\n[2/2] Faolsiz mijozlar (7+ kun)...")
        sent_a = _send_inactive_reminders(self.stdout)
        self.stdout.write(self.style.SUCCESS(f"  -> Yuborildi: {sent_a}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nUmumiy: {sent_u + sent_a} ta eslatma yuborildi."
        ))
