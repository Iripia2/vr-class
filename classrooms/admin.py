from django.contrib import admin
from .models import Classroom, Enrollment, Lesson, ClassSession

admin.site.register(Classroom)
admin.site.register(Enrollment)
admin.site.register(Lesson)
admin.site.register(ClassSession)
