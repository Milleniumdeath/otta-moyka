from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User


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

    def __str__(self):
        return f"{self.worker.get_full_name()} — {self.get_service_type_display()}"
