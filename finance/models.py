from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Expense(models.Model):
    """Chiqimlar modeli"""

    class Category(models.TextChoices):
        # Kommunal
        GAS         = 'gas',        _('Gaz')
        WATER       = 'water',      _('Suv')
        ELECTRICITY = 'electricity',_('Elektr')
        # Xom ashyo
        CHEMICAL    = 'chemical',   _('Kimyoviy modda')
        FOAM        = 'foam',       _('Pena')
        SPARE_PART  = 'spare_part', _('Ehtiyot qism')
        TOOL        = 'tool',       _('Ish qurol')
        # Tashqi
        EXTERNAL    = 'external',   _('Tashqi chiqim')

    class Group(models.TextChoices):
        COMMUNAL = 'communal', _('Kommunal chiqimlar')
        RAW      = 'raw',      _('Xom ashyo chiqimlari')
        EXTERNAL = 'external', _('Tashqi chiqimlar')

    category    = models.CharField(max_length=20, choices=Category.choices, verbose_name=_('Kategoriya'))
    group       = models.CharField(max_length=20, choices=Group.choices, verbose_name=_('Guruh'))
    description = models.CharField(max_length=200, blank=True, verbose_name=_('Izoh'))
    amount      = models.DecimalField(max_digits=12, decimal_places=0, verbose_name=_("Miqdor (so'm)"))
    date        = models.DateField(default=timezone.now, verbose_name=_('Sana'))
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Chiqim')
        verbose_name_plural = _('Chiqimlar')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_category_display()} — {self.amount} so'm ({self.date})"


class Income(models.Model):
    """Kirimlar modeli"""

    class Category(models.TextChoices):
        OFFLINE  = 'offline',  _('Oflayn xizmat')
        ONLINE   = 'online',   _('Onlayn buyurtma (avtomatik)')
        EXTRA    = 'extra',    _('Qo\'shimcha xizmat')

    category    = models.CharField(max_length=20, choices=Category.choices, verbose_name=_('Kategoriya'))
    description = models.CharField(max_length=200, blank=True, verbose_name=_('Izoh / Xizmat nomi'))
    amount      = models.DecimalField(max_digits=12, decimal_places=0, verbose_name=_("Miqdor (so'm)"))
    order       = models.ForeignKey(
        'core.Order', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='incomes',
        verbose_name=_('Bog\'liq buyurtma')
    )
    date        = models.DateField(default=timezone.now, verbose_name=_('Sana'))
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Kirim')
        verbose_name_plural = _('Kirimlar')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_category_display()} — {self.amount} so'm ({self.date})"
