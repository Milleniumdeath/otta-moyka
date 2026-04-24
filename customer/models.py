from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User


class Car(models.Model):
    """Mijozning mashinasi"""

    class CarType(models.TextChoices):
        LIGHT = 'light', _('Yengil mashina')
        HEAVY = 'heavy', _('Yuk mashina')

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cars',
        limit_choices_to={'role': 'customer'},
        verbose_name=_('Egasi')
    )
    car_type = models.CharField(
        max_length=10,
        choices=CarType.choices,
        default=CarType.LIGHT,
        verbose_name=_('Mashina turi')
    )
    brand = models.CharField(max_length=50, verbose_name=_('Rusumi (Chevrolet, Nexia...)'))
    model = models.CharField(max_length=50, verbose_name=_('Modeli'))
    plate_number = models.CharField(max_length=15, verbose_name=_('Davlat raqami'))
    image = models.ImageField(
        upload_to='cars/',
        blank=True, null=True,
        verbose_name=_('Mashina rasmi')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Mashina')
        verbose_name_plural = _('Mashinalar')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.brand} {self.model} — {self.plate_number}"
