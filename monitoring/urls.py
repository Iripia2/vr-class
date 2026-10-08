from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    path('consent/session/<int:session_id>/', views.toggle_consent, name='toggle_consent'),
    path('api/record-emotion/', views.record_emotion, name='record_emotion'),
    path('session/<int:session_id>/check-in/', views.submit_session_checkin, name='session_checkin'),
    path('session/<int:pk>/report/', views.session_report, name='session_report'),
]
