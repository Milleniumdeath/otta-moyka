from django import forms
from .models import PriceList

class PriceListForm(forms.ModelForm):
    class Meta:
        model = PriceList
        fields = ['service_type', 'min_price', 'max_price', 'recommended_price', 'description', 'is_active']
        widgets = {
            'service_type':      forms.Select(attrs={'class': 'form-control'}),
            'min_price':         forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Masalan: 30000'}),
            'max_price':         forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Masalan: 80000'}),
            'recommended_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Masalan: 50000'}),
            'description':       forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_active':         forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned = super().clean()
        min_p = cleaned.get('min_price')
        max_p = cleaned.get('max_price')
        rec_p = cleaned.get('recommended_price')
        if min_p and max_p and min_p >= max_p:
            raise forms.ValidationError("Minimal narx maksimaldan kichik bo'lishi kerak!")
        if rec_p and min_p and max_p:
            if not (min_p <= rec_p <= max_p):
                raise forms.ValidationError("Tavsiya etilgan narx min va max orasida bo'lishi kerak!")
        return cleaned

