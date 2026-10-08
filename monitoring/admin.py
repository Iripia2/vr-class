from django.contrib import admin
from .models import ConsentRecord, EmotionEvent

admin.site.register(ConsentRecord)
admin.site.register(EmotionEvent)
