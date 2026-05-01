from django import forms
from .models import ServiceAd, WorkSchedule

class ServiceAdForm(forms.ModelForm):
    class Meta:
        model = ServiceAd
        fields = ['title', 'description', 'service_type', 'price']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sarlavha...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Tajriba...'}),
            'service_type': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '50000', 'min': '1000'}),
        }
        labels = {
            'title': 'Sarlavha',
            'description': 'Tavsif',
            'service_type': 'Xizmat turi',
            'price': 'Narx (so‘m)',
        }

class WorkScheduleForm(forms.ModelForm):
    class Meta:
        model = WorkSchedule
        fields = ['weekday', 'start_time', 'end_time', 'is_active']
        widgets = {
            'weekday':    forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time':   forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'weekday':    'Hafta kuni',
            'start_time': 'Boshlanish',
            'end_time':   'Tugash',
            'is_active':  'Ish kuni',
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end   = cleaned.get('end_time')
        if start and end and start >= end:
            raise forms.ValidationError("Boshlanish vaqti tugash vaqtidan kichik bo'lishi kerak!")
        return cleaned
