from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='app/login.html'), name='logout'),
    
    path('profile/', views.profile, name='profile'),
    path('profile/photo/', views.profile_photo, name='profile_photo'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('history/', views.patient_history, name='history'),
    path('patient/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('patient/<int:pk>/edit/', views.edit_patient, name='edit_patient'),
    path('add-patient/', views.add_patient, name='add_patient'),
    path('appointments/', views.appointment_list, name='appointments'),
    path('appointments/new/', views.add_appointment, name='add_appointment'),
    path('appointments/<int:pk>/status/', views.update_appointment_status, name='appointment_status'),
    path('upload/', views.upload_image, name='upload'),
    path('result/<int:pk>/', views.result, name='result'),
    path('result/<int:pk>/image/', views.retina_image_file, name='retina_image_file'),
]
