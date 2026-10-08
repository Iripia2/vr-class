from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        TEACHER = 'teacher', 'Teacher'

    role = models.CharField(max_length=10, choices=Role.choices)
    full_name = models.CharField(max_length=150)

    def is_teacher(self):
        return self.role == self.Role.TEACHER

    def is_student(self):
        return self.role == self.Role.STUDENT

    def __str__(self):
        return self.full_name or self.username
