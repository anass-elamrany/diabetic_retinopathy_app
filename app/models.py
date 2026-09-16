# app/models.py (as you provided)
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

class User(AbstractUser):
    hospital = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

class Patient(models.Model):
    """Patient information model"""
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )
    
    patient_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_patients')

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.patient_id})"

class RetinaImage(models.Model):
    STAGES = [
        (0, 'No DR'),
        (1, 'Mild'),
        (2, 'Moderate'),
        (3, 'Severe'),
        (4, 'Proliferative DR'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='retina_images')
    image = models.ImageField(upload_to='retina_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    stage = models.IntegerField(choices=STAGES, null=True, blank=True)
    confidence = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    notes = models.TextField(blank=True)
    analyzed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='analyzed_images')
    
    def __str__(self):
        return f"Image for {self.patient} - Stage {self.stage}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    scheduled_at = models.DateTimeField()
    reason = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='scheduled')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_at']

    def __str__(self):
        return f"{self.patient} on {self.scheduled_at:%Y-%m-%d %H:%M}"
