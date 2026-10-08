from django.conf import settings
from django.db import models
from django.db.models import Q


class ConsentRecord(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consents')
    classroom = models.ForeignKey('classrooms.Classroom', on_delete=models.CASCADE, related_name='consents')
    session = models.ForeignKey(
        'classrooms.ClassSession',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='consent_records',
    )
    active = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('student', 'session'),
                condition=Q(session__isnull=False),
                name='unique_student_session_consent',
            ),
        ]

    def __str__(self):
        return f'{self.student} / {self.classroom} — {"on" if self.active else "off"}'


class EmotionEvent(models.Model):
    LABEL_CHOICES = [
        ('neutral_steady', 'Neutral / steady expression pattern'),
        ('positive_expression', 'Positive expression pattern'),
        ('negative_expression', 'Negative expression pattern'),
        ('surprise_like', 'Surprise-like expression pattern'),
        ('uncertain', 'Uncertain signal'),
        ('low_confidence', 'Low-confidence signal'),
        ('no_face', 'No face detected'),
    ]

    session = models.ForeignKey('classrooms.ClassSession', on_delete=models.CASCADE, related_name='emotion_events')
    label = models.CharField(max_length=20, choices=LABEL_CHOICES)
    confidence = models.FloatField(default=0.0)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.session} — {self.label} ({self.confidence:.2f})'


class SessionCheckIn(models.Model):
    class Response(models.TextChoices):
        ON_TRACK = 'on_track', 'Following comfortably'
        ANOTHER_EXAMPLE = 'another_example', 'Would like another example'
        TOO_FAST = 'too_fast', 'The pace feels too fast'
        NEED_PAUSE = 'need_pause', 'I need a short pause'

    session = models.ForeignKey(
        'classrooms.ClassSession',
        on_delete=models.CASCADE,
        related_name='check_ins',
    )
    response = models.CharField(max_length=24, choices=Response.choices)

    class Meta:
        indexes = [
            models.Index(fields=('session', 'response'), name='checkin_session_response_idx'),
        ]

    def __str__(self):
        return f'{self.session} — class check-in'
