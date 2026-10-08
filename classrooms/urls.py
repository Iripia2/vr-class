from django.urls import path
from . import views

app_name = 'classrooms'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('classroom/create/', views.create_classroom, name='create_classroom'),
    path('classroom/join/', views.join_classroom, name='join_classroom'),
    path('classroom/<int:pk>/', views.classroom_detail, name='classroom_detail'),
    path('classroom/<int:pk>/lesson/add/', views.add_lesson, name='add_lesson'),
    path('classroom/<int:pk>/session/start/', views.start_session, name='start_session'),
    path('session/<int:pk>/end/', views.end_session, name='end_session'),
    path('session/<int:pk>/', views.virtual_classroom, name='virtual_classroom'),
]
