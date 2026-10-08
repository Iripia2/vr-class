from django import forms
from .models import Classroom, Lesson


class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['name', 'subject']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
        }


class JoinClassroomForm(forms.Form):
    join_code = forms.CharField(max_length=8, label='Join code')


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
