from django.db import models

class PriceList(models.Model):
    """Moyka egasi xizmat turlari uchun narx chegaralarini belgilaydi"""

    class ServiceType(models.TextChoices):
        LIGHT    = 'light',    'Engil avtomobil'
        HEAVY    = 'heavy',    'Og\'ir transport'
        POLISH   = 'polish',   'Polishing'
        INTERIOR = 'interior', 'Salon tozalash'
        FULL     = 'full',     'To\'liq kompleks'

    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        unique=True,
        verbose_name='Xizmat turi'
    )
    min_price = models.DecimalField(
        max_digits=10, decimal_places=0,
        verbose_name='Minimal narx (so\'m)'
    )
    max_price = models.DecimalField(
        max_digits=10, decimal_places=0,
        verbose_name='Maksimal narx (so\'m)'
    )
    recommended_price = models.DecimalField(
        max_digits=10, decimal_places=0,
        null=True, blank=True,
        verbose_name='Tavsiya etilgan narx'
    )
    description = models.TextField(blank=True, verbose_name='Tavsif')
    is_active = models.BooleanField(default=True, verbose_name='Faol')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Narx ro\'yxati'
        verbose_name_plural = 'Narx ro\'yxatlari'
        ordering = ['service_type']

    def __str__(self):
        return f"{self.get_service_type_display()}: {self.min_price}–{self.max_price} so'm"


