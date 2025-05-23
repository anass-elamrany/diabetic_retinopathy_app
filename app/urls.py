from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='app/login.html'), name='logout'),
    
    path('profile/', views.profile, name='profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('history/', views.patient_history, name='history'),
    path('patient/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('add-patient/', views.add_patient, name='add_patient'),
    path('upload/', views.upload_image, name='upload'),
    path('result/<int:pk>/', views.result, name='result'),
]