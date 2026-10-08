from django import forms

from .models import SessionCheckIn


class SessionCheckInForm(forms.ModelForm):
    class Meta:
        model = SessionCheckIn
        fields = ['response']
        widgets = {
            'response': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        }