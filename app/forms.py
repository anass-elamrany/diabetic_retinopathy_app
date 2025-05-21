# app/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Patient, RetinaImage

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    hospital = forms.CharField(max_length=100, required=True)
    license_number = forms.CharField(max_length=50, required=True)
    phone_number = forms.CharField(max_length=20, required=True)
    profile_picture = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2',
                  'hospital', 'license_number', 'phone_number', 'profile_picture']

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 
                  'hospital', 'license_number', 'phone_number', 'profile_picture']

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['patient_id', 'first_name', 'last_name', 'date_of_birth', 
                 'gender', 'email', 'phone', 'address', 'medical_history']

class RetinaImageForm(forms.ModelForm):
    class Meta:
        model = RetinaImage
        fields = ['patient', 'image', 'notes']