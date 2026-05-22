from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User


class Order(models.Model):
    """Buyurtma — mijoz ishchidan xizmat so'raydi"""

    class Status(models.TextChoices):
        PENDING   = 'pending',   _('Kutilmoqda')
        ACCEPTED  = 'accepted',  _('Qabul qilindi')
        IN_PROGRESS = 'in_progress', _('Jarayonda')
        COMPLETED = 'completed', _('Yakunlandi')
        REJECTED  = 'rejected',  _('Rad etildi')
        CANCELLED = 'cancelled', _('Bekor qilindi')

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='customer_orders',
        limit_choices_to={'role': 'customer'},
        verbose_name=_('Mijoz')
    )
    worker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='worker_orders',
        limit_choices_to={'role': 'worker'},
        verbose_name=_('Ishchi')
    )
    car = models.ForeignKey(
        'customer.Car',
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders',
        verbose_name=_('Mashina')
    )
    service_ad = models.ForeignKey(
        'worker.ServiceAd',
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders',
        verbose_name=_("Xizmat e'loni")
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_('Holati')
    )
    note = models.TextField(
        blank=True, null=True,
        verbose_name=_("Mijoz izohi")
    )
    total_price = models.DecimalField(
        max_digits=10, decimal_places=0,
        default=0,
        verbose_name=_("Narx (so'm)")
    )
    scheduled_time = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Buyurtma vaqti'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Qabul qilingan vaqt')
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    # Buyurtmani yakunlash uchun qabul qilingandan beri o'tishi shart bo'lgan vaqt.
    # Yengil mashina — 20 daqiqa, yuk mashina — 50 daqiqa.
    LIGHT_WORK_MINUTES = 20
    HEAVY_WORK_MINUTES = 50

    class Meta:
        verbose_name = _('Buyurtma')
        verbose_name_plural = _('Buyurtmalar')
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.pk} | {self.customer} → {self.worker} | {self.get_status_display()}"

    def minutes_since_accepted(self):
        """Buyurtma qabul qilinganidan beri necha daqiqa o'tdi.

        accepted_at bo'lmasa (eski buyurtmalar) updated_at ga tayanadi.
        """
        from django.utils import timezone
        ref = self.accepted_at or self.updated_at
        if not ref:
            return None
        return (timezone.now() - ref).total_seconds() / 60

    def is_heavy_wash(self):
        """Buyurtma yuk mashina yuvishimi."""
        if self.service_ad and getattr(self.service_ad, 'service_type', '') == 'heavy':
            return True
        if self.car and getattr(self.car, 'car_type', '') == 'heavy':
            return True
        return False

    def required_work_minutes(self):
        """Yakunlash uchun zarur minimal daqiqa — mashina turiga bog'liq."""
        return self.HEAVY_WORK_MINUTES if self.is_heavy_wash() else self.LIGHT_WORK_MINUTES

    def can_be_completed(self):
        """Yakunlash mumkinmi — zarur daqiqa o'tganmi (mashina turiga qarab)."""
        m = self.minutes_since_accepted()
        return m is not None and m >= self.required_work_minutes()

    def minutes_left_to_complete(self):
        """Yakunlashga necha daqiqa qolgani (yuqoriga yaxlitlangan)."""
        import math
        m = self.minutes_since_accepted()
        if m is None:
            return 0
        return max(0, math.ceil(self.required_work_minutes() - m))

    def is_scheduled(self):
        return self.scheduled_time is not None

    def get_display_time(self):
        from django.utils import timezone
        if self.scheduled_time:
            local = timezone.localtime(self.scheduled_time)
            return local.strftime("%d-%m-%Y %H:%M")
        return "Hozir"

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    @property
    def is_rejected(self):
        return self.status == self.Status.REJECTED


class Review(models.Model):
    """5 yulduzli baho — buyurtma yakunlangandan keyin"""

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name=_('Buyurtma')
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_given',
        verbose_name=_('Baholovchi')
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Yulduz (1-5)')
    )
    comment = models.TextField(
        blank=True, null=True,
        verbose_name=_('Izoh')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Baho')
        verbose_name_plural = _('Baholar')
        ordering = ['-created_at']

    def __str__(self):
        return f"{'⭐' * self.rating} — {self.order}"


class LoyaltyToken(models.Model):
    """Sodiqlik tangalari hisobi"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='loyalty',
        verbose_name=_('Foydalanuvchi')
    )
    balance = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tangalar soni')
    )
    total_earned = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Jami yig\'ilgan')
    )
    total_spent = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Jami sarflangan')
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Sodiqlik tangasi')
        verbose_name_plural = _('Sodiqlik tangalari')

    def __str__(self):
        return f"{self.user} — {self.balance} tanga"

    def add_tokens(self, amount):
        """Tanga qo'shish"""
        self.balance += amount
        self.total_earned += amount
        self.save()

    def spend_tokens(self, amount):
        """Tanga sarflash — yetarli bo'lsa True qaytaradi"""
        if self.balance >= amount:
            self.balance -= amount
            self.total_spent += amount
            self.save()
            return True
        return False

    @property
    def loyalty_percentage(self):
        """Sodiqlik darajasi % (har 10 muvaffaqiyatli buyurtma = 100%)"""
        from django.conf import settings
        needed = getattr(settings, 'LOYALTY_FULL_PERCENTAGE', 10)
        completed = Order.objects.filter(
            models.Q(customer=self.user) | models.Q(worker=self.user),
            status=Order.Status.COMPLETED
        ).count()
        return min(int((completed / needed) * 100), 100)


class LoyaltyTransaction(models.Model):
    """Tanga harakatlari tarixi"""

    class TxType(models.TextChoices):
        EARN  = 'earn',  _('Yig\'ildi')
        SPEND = 'spend', _('Sarflandi')

    loyalty = models.ForeignKey(
        LoyaltyToken,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('Hisob')
    )
    tx_type = models.CharField(
        max_length=10,
        choices=TxType.choices,
        verbose_name=_('Turi')
    )
    amount = models.PositiveIntegerField(verbose_name=_('Miqdor'))
    description = models.CharField(max_length=200, verbose_name=_('Izoh'))
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Buyurtma')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Tanga tranzaksiyasi')
        verbose_name_plural = _('Tanga tranzaksiyalari')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_tx_type_display()} {self.amount} tanga — {self.loyalty.user}"


class Bonus(models.Model):
    """Moyka egasi tomonidan yaratilgan bonus texnikalar"""

    name = models.CharField(max_length=100, verbose_name=_('Buyum nomi'))
    description = models.TextField(blank=True, verbose_name=_('Tavsif'))
    image = models.ImageField(
        upload_to='bonuses/',
        blank=True, null=True,
        verbose_name=_('Rasm')
    )
    token_cost = models.PositiveIntegerField(
        verbose_name=_('Narxi (tanga)')
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Miqdori')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Faol'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Bonus')
        verbose_name_plural = _('Bonuslar')
        ordering = ['token_cost']

    def __str__(self):
        return f"{self.name} — {self.token_cost} tanga ({self.quantity} ta)"

    @property
    def is_available(self):
        return self.is_active and self.quantity > 0

    def claim(self, user):
        """Foydalanuvchi bonus oladi"""
        loyalty, _ = LoyaltyToken.objects.get_or_create(user=user)
        if not self.is_available:
            return False, "Bonus mavjud emas yoki tugagan"
        if not loyalty.spend_tokens(self.token_cost):
            return False, "Tangalar yetarli emas"
        self.quantity -= 1
        self.save()
        LoyaltyTransaction.objects.create(
            loyalty=loyalty,
            tx_type=LoyaltyTransaction.TxType.SPEND,
            amount=self.token_cost,
            description=f"Bonus olindi: {self.name}"
        )
        return True, "Bonus muvaffaqiyatli olindi!"


class BonusClaim(models.Model):
    """Kim qaysi bonusni olgani"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='claimed_bonuses',
        verbose_name=_('Foydalanuvchi')
    )
    bonus = models.ForeignKey(
        Bonus,
        on_delete=models.CASCADE,
        related_name='claims',
        verbose_name=_('Bonus')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Olingan bonus')
        verbose_name_plural = _('Olingan bonuslar')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.bonus.name}"

from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """Bildirishnomalar modeli"""

    class Type(models.TextChoices):
        NEW_ORDER    = 'new_order',    _('Yangi buyurtma')
        ORDER_ACCEPT = 'order_accept', _('Buyurtma qabul qilindi')
        ORDER_REJECT = 'order_reject', _('Buyurtma rad etildi')
        ORDER_DONE   = 'order_done',   _('Buyurtma yakunlandi')
        NEW_WORKER   = 'new_worker',   _('Yangi ishchi so\'rovi')
        WORKER_APPROVED = 'worker_approved', _('Ishchi tasdiqlandi')
        BONUS_CLAIMED   = 'bonus_claimed',   _('Bonus olindi')

    user       = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='notifications', verbose_name=_('Foydalanuvchi')
    )
    notif_type = models.CharField(
        max_length=20, choices=Type.choices,
        verbose_name=_('Turi')
    )
    title   = models.CharField(max_length=100, verbose_name=_('Sarlavha'))
    message = models.TextField(verbose_name=_('Xabar'))
    icon    = models.CharField(max_length=50, default='fa-bell')
    color   = models.CharField(max_length=20, default='cyan')
    url     = models.CharField(max_length=200, default='#', blank=True)
    is_read = models.BooleanField(default=False, verbose_name=_('O\'qilgan'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Bildirishnoma')
        verbose_name_plural = _('Bildirishnomalar')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.title}"


class WeatherCache(models.Model):
    """Kunlik ob-havo kesh ma'lumoti"""
    city = models.CharField(max_length=100, default="Oltiariq")
    date = models.DateField()
    rain_probability = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Yomg'ir yog'ish ehtimoli foizda"
    )
    description = models.CharField(max_length=200, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('city', 'date')
        verbose_name = "Ob-havo"
        verbose_name_plural = "Ob-havo ma'lumotlari"

    def __str__(self):
        return f"{self.city} {self.date}: {self.rain_probability}%"
