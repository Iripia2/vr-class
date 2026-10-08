import random
import string

from django.conf import settings
from django.db import models


def generate_join_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class Classroom(models.Model):
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=100, blank=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='classrooms_taught'
    )
    join_code = models.CharField(max_length=8, unique=True, default=generate_join_code)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments'
    )
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='enrollments')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'classroom')

    def __str__(self):
        return f'{self.student} in {self.classroom}'


class Lesson(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ClassSession(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='sessions')
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.classroom} session #{self.pk}'
