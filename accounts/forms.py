from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, label='Full name')
    email = forms.EmailField(label='Email address')
    role = forms.ChoiceField(choices=User.Role.choices, widget=forms.RadioSelect)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'username', 'role', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'role':
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.full_name = self.cleaned_data['full_name']
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user
