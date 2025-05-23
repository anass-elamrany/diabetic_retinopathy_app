# app/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegisterForm, UserUpdateForm, PatientForm, RetinaImageForm
from .models import Patient, RetinaImage
from .utils import DRModel
import os
from django.conf import settings
from .charts import get_chart_data 
import os
from django.conf import settings
import json
from datetime import datetime

dr_model = DRModel()

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'app/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)
    
    context = {
        'form': form
    }
    return render(request, 'app/profile.html', context)

@login_required
def dashboard(request):
    try:
        # Basic stats
        total_patients = Patient.objects.filter(created_by=request.user).count()
        recent_patients = Patient.objects.filter(created_by=request.user).order_by('-created_at')[:5]
        recent_images = RetinaImage.objects.filter(analyzed_by=request.user).order_by('-uploaded_at')[:5]
        
        # Get chart data
        chart_data = get_chart_data(request.user)
        
        # Prepare context with properly formatted JSON data
        context = {
            'total_patients': total_patients,
            'recent_patients': recent_patients,
            'recent_images': recent_images,
            'total_analyses': RetinaImage.objects.filter(analyzed_by=request.user).count(),
            'high_risk_cases': RetinaImage.objects.filter(analyzed_by=request.user, stage__gte=3).count(),
            'this_month_analyses': RetinaImage.objects.filter(
                analyzed_by=request.user,
                uploaded_at__month=datetime.now().month,
                uploaded_at__year=datetime.now().year
            ).count(),
            'stage_data': json.dumps(chart_data['stage_data'].get('data', [])),
            'monthly_labels': json.dumps(chart_data['monthly_data'].get('labels', [])),
            'monthly_data': json.dumps(chart_data['monthly_data'].get('data', [])),
            'chart_errors': {
                'stage': chart_data['stage_data'].get('error', ''),
                'monthly': chart_data['monthly_data'].get('error', '')
            }
        }
        return render(request, 'app/dashboard.html', context)
        
    except Exception as e:
        return render(request, 'app/dashboard.html', {
            'chart_errors': {
                'general': str(e),
                'stage': "Error loading dashboard",
                'monthly': "Error loading dashboard"
            }
        })


@login_required
def patient_history(request):
    patients = Patient.objects.filter(created_by=request.user)
    context = {
        'patients': patients
    }
    return render(request, 'app/history.html', context)

@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk, created_by=request.user)
    images = patient.retina_images.all()
    
    context = {
        'patient': patient,
        'images': images
    }
    return render(request, 'app/patient_detail.html', context)

@login_required
def add_patient(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.save()
            messages.success(request, 'Patient added successfully!')
            return redirect('history')
    else:
        form = PatientForm()
    
    context = {
        'form': form
    }
    return render(request, 'app/add_patient.html', context)

@login_required
def upload_image(request):
    if request.method == 'POST':
        form = RetinaImageForm(request.POST, request.FILES)
        if form.is_valid():
            retina_image = form.save(commit=False)
            retina_image.analyzed_by = request.user
            
            # Save the image first to get the path
            retina_image.save()
            
            # Get the full path to the image
            image_path = os.path.join(settings.MEDIA_ROOT, str(retina_image.image))
            
            # Make prediction
            prediction = dr_model.predict(image_path)
            
            # Update the model with prediction results
            retina_image.stage = prediction['class']
            retina_image.confidence = prediction['confidence']
            retina_image.save()
            
            messages.success(request, 'Image uploaded and analyzed successfully!')
            return redirect('result', pk=retina_image.id)
    else:
        form = RetinaImageForm()
    
    # Only show patients created by the current user
    form.fields['patient'].queryset = Patient.objects.filter(created_by=request.user)
    
    context = {
        'form': form
    }
    return render(request, 'app/upload.html', context)

@login_required
def result(request, pk):
    retina_image = get_object_or_404(RetinaImage, pk=pk, analyzed_by=request.user)
    
    # Get human-readable stage
    stage_display = dict(RetinaImage.STAGES).get(retina_image.stage)
    
    context = {
        'image': retina_image,
        'stage_display': stage_display,
        'confidence_percentage': round(retina_image.confidence * 100, 2) if retina_image.confidence else None,
    }
    return render(request, 'app/result.html', context)