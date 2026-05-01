from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from django.db import models
from accounts.models import User
from django.core.exceptions import ValidationError

class WorkSchedule(models.Model):
    """Ishchi haftalik ish jadvalini belgilaydi"""

    class Weekday(models.IntegerChoices):
        MONDAY    = 0, 'Dushanba'
        TUESDAY   = 1, 'Seshanba'
        WEDNESDAY = 2, 'Chorshanba'
        THURSDAY  = 3, 'Payshanba'
        FRIDAY    = 4, 'Juma'
        SATURDAY  = 5, 'Shanba'
        SUNDAY    = 6, 'Yakshanba'

    worker     = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='Ishchi'
    )
    weekday    = models.IntegerField(
        choices=Weekday.choices,
        verbose_name='Hafta kuni'
    )
    start_time = models.TimeField(verbose_name='Boshlanish vaqti')
    end_time   = models.TimeField(verbose_name='Tugash vaqti')
    is_active  = models.BooleanField(default=True, verbose_name='Ish kuni')

    class Meta:
        verbose_name = 'Ish jadvali'
        verbose_name_plural = 'Ish jadvallari'
        unique_together = ('worker', 'weekday')
        ordering = ['weekday']

    def __str__(self):
        return f"{self.worker.get_full_name()} — {self.get_weekday_display()} {self.start_time}–{self.end_time}"

    def is_working_now(self):
        """Hozir ishchi ish vaqtida ekanligini tekshiradi"""
        from django.utils import timezone
        now = timezone.localtime()
        if now.weekday() != self.weekday:
            return False
        return self.start_time <= now.time() <= self.end_time



class ServiceAd(models.Model):
    """Ishchi tomonidan yaratilgan xizmat e'loni"""

    class ServiceType(models.TextChoices):
        LIGHT_CAR   = 'light',  _('Yengil mashina')
        HEAVY_CAR   = 'heavy',  _('Yuk mashina')
        POLISH      = 'polish', _('Polировka')
        INTERIOR    = 'interior', _('Salon tozalash')
        FULL        = 'full',   _('To\'liq kompleks')

    worker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='service_ads',
        limit_choices_to={'role': 'worker'},
        verbose_name=_('Ishchi')
    )
    title = models.CharField(max_length=100, verbose_name=_('Sarlavha'))
    description = models.TextField(verbose_name=_('Tavsif / Tajriba'))
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        verbose_name=_('Xizmat turi')
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=0,
        verbose_name=_("Narx (so'm)")
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Faol'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Xizmat e'loni")
        verbose_name_plural = _("Xizmat e'lonlari")
        ordering = ['-created_at']

    def clean(self):
        """Narx egasi belgilagan chegarada ekanligini tekshiradi"""
        try:
            from owner.models import PriceList
            pricelist = PriceList.objects.filter(
                service_type=self.service_type,
                is_active=True
            ).first()

            if pricelist:
                if self.price < pricelist.min_price:
                    raise ValidationError(
                        f"Narx {pricelist.min_price:,} so'mdan kam bo'lmasligi kerak!"
                    )
                if self.price > pricelist.max_price:
                    raise ValidationError(
                        f"Narx {pricelist.max_price:,} so'mdan oshmasligi kerak!"
                    )
        except ImportError:
            pass

    def save(self, *args, **kwargs):
        # self.full_clean()  # save dan oldin clean() chaqiriladi
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.worker.get_full_name()} — {self.get_service_type_display()}"
