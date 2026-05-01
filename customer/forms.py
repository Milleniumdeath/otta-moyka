from django import forms
from core.models import Order

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model  = Order
        fields = ['note', 'scheduled_time']
        widgets = {
            'note': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Qo\'shimcha izoh (ixtiyoriy)'
            }),
            'scheduled_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
        }
        labels = {
            'note':           'Izoh',
            'scheduled_time': 'Buyurtma vaqti (bo\'sh qoldirsangiz hozir deb hisoblanadi)',
        }

    def clean_scheduled_time(self):
        from django.utils import timezone
        dt = self.cleaned_data.get('scheduled_time')
        if dt and dt <= timezone.now():
            raise forms.ValidationError("Buyurtma vaqti kelajakda bo'lishi kerak!")
        return dt

