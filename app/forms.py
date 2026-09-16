# app/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Patient, RetinaImage, Appointment
from django.utils import timezone


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs.setdefault('class', css_class)

    def clean_profile_picture(self):
        image = self.cleaned_data.get('profile_picture')
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Profile photos must be 5 MB or smaller.')
        return image

class UserRegisterForm(StyledFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    hospital = forms.CharField(max_length=100, required=True)
    license_number = forms.CharField(max_length=50, required=True)
    phone_number = forms.CharField(max_length=20, required=True)
    profile_picture = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2',
                  'hospital', 'license_number', 'phone_number', 'profile_picture']

class UserUpdateForm(StyledFormMixin, forms.ModelForm):
    email = forms.EmailField()
    remove_photo = forms.BooleanField(required=False, label='Remove current photo')
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 
                  'hospital', 'license_number', 'phone_number', 'profile_picture']
        widgets = {'profile_picture': forms.FileInput(attrs={'accept': 'image/png,image/jpeg,image/webp'})}

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('remove_photo') and 'profile_picture' in self.files:
            raise forms.ValidationError('Choose a new photo or remove the current one.')
        return cleaned_data

    def save(self, commit=True):
        old_photo = self.instance.profile_picture if self.cleaned_data.get('remove_photo') else None
        user = super().save(commit=False)
        if old_photo:
            user.profile_picture = None
        if commit:
            user.save()
            if old_photo:
                old_photo.delete(save=False)
        return user

class PatientForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['patient_id', 'first_name', 'last_name', 'date_of_birth', 
                  'gender', 'email', 'phone', 'address', 'medical_history']
        widgets = {'date_of_birth': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data['date_of_birth']
        if date_of_birth > timezone.localdate():
            raise forms.ValidationError('Date of birth cannot be in the future.')
        return date_of_birth

class RetinaImageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = RetinaImage
        fields = ['patient', 'image', 'notes']

    def clean_image(self):
        image = self.cleaned_data['image']
        if image.size > 10 * 1024 * 1024:
            raise forms.ValidationError('Retinal images must be 10 MB or smaller.')
        return image


class AppointmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['patient', 'scheduled_at', 'reason', 'notes']
        labels = {'scheduled_at': 'Date and time'}
        widgets = {
            'scheduled_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['patient'].queryset = Patient.objects.filter(created_by=user).order_by('last_name', 'first_name')

    def clean_scheduled_at(self):
        scheduled_at = self.cleaned_data['scheduled_at']
        if scheduled_at <= timezone.now():
            raise forms.ValidationError('Choose a future date and time.')
        if Appointment.objects.filter(
            created_by=self.user, scheduled_at=scheduled_at, status='scheduled'
        ).exists():
            raise forms.ValidationError('You already have an appointment at this time.')
        return scheduled_at
