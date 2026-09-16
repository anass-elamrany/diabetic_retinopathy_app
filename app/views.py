# app/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST
from .forms import UserRegisterForm, UserUpdateForm, PatientForm, RetinaImageForm, AppointmentForm
from .models import Patient, RetinaImage, Appointment
from .utils import DRModel
import logging
import mimetypes
import os

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.http import FileResponse, Http404
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .charts import get_chart_data

logger = logging.getLogger(__name__)

dr_model = DRModel()


class LoginView(auth_views.LoginView):
    template_name = 'app/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allow_registration'] = settings.ALLOW_PUBLIC_REGISTRATION
        return context

def register(request):
    if not settings.ALLOW_PUBLIC_REGISTRATION:
        raise Http404
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
        analyses = RetinaImage.objects.filter(analyzed_by=request.user, confidence__gt=0)
        recent_images = analyses.order_by('-uploaded_at')[:5]
        appointments = Appointment.objects.filter(created_by=request.user)
        upcoming = appointments.filter(status='scheduled', scheduled_at__gte=timezone.now())
        
        # Get chart data
        chart_data = get_chart_data(request.user)
        stage_counts = chart_data['stage_data'].get('data', [0] * 5)
        largest_stage = max(stage_counts, default=0) or 1
        monthly_labels = chart_data['monthly_data'].get('labels', [])
        monthly_counts = chart_data['monthly_data'].get('data', [])
        largest_month = max(monthly_counts, default=0) or 1
        
        current_month = timezone.localdate()
        context = {
            'total_patients': total_patients,
            'recent_patients': recent_patients,
            'recent_images': recent_images,
            'upcoming_appointments': upcoming.select_related('patient').order_by('scheduled_at')[:5],
            'upcoming_count': upcoming.count(),
            'completed_count': appointments.filter(status='completed').count(),
            'total_analyses': analyses.count(),
            'high_risk_cases': analyses.filter(stage__gte=3).count(),
            'this_month_analyses': analyses.filter(
                uploaded_at__month=current_month.month,
                uploaded_at__year=current_month.year
            ).count(),
            'chart_errors': {
                'stage': chart_data['stage_data'].get('error', ''),
                'monthly': chart_data['monthly_data'].get('error', '')
            },
            'stage_rows': [(label, count, round(count / largest_stage * 100)) for (_, label), count in zip(RetinaImage.STAGES, stage_counts)],
            'monthly_rows': [(label, count, round(count / largest_month * 100)) for label, count in zip(monthly_labels, monthly_counts)],
        }
        return render(request, 'app/dashboard.html', context)
        
    except Exception:
        logger.exception('Failed to load dashboard')
        return render(request, 'app/dashboard.html', {
            'chart_errors': {
                'general': 'The dashboard could not be loaded. Please try again.',
            }
        })


@login_required
def patient_history(request):
    query = request.GET.get('q', '').strip()[:100]
    patients = Patient.objects.filter(created_by=request.user)
    if query:
        for term in query.split():
            patients = patients.filter(
                Q(patient_id__icontains=term) | Q(first_name__icontains=term)
                | Q(last_name__icontains=term) | Q(phone__icontains=term)
            )
    patients = patients.order_by('last_name', 'first_name')
    context = {
        'patients': patients,
        'query': query,
    }
    return render(request, 'app/history.html', context)

@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk, created_by=request.user)
    images = patient.retina_images.filter(analyzed_by=request.user)
    appointments = patient.appointments.filter(created_by=request.user).order_by('-scheduled_at')[:5]
    
    context = {
        'patient': patient,
        'images': images,
        'appointments': appointments,
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
def edit_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk, created_by=request.user)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient record updated.')
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'app/add_patient.html', {'form': form, 'patient': patient})


@login_required
def appointment_list(request):
    appointments = Appointment.objects.filter(created_by=request.user).select_related('patient')
    upcoming = appointments.filter(status='scheduled', scheduled_at__gte=timezone.now())
    other = appointments.exclude(pk__in=upcoming.values('pk')).order_by('-scheduled_at')
    return render(request, 'app/appointments.html', {'upcoming': upcoming, 'other': other})


@login_required
def add_appointment(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST, user=request.user)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.created_by = request.user
            appointment.save()
            messages.success(request, 'Appointment scheduled.')
            return redirect('appointments')
    else:
        initial = {}
        patient_id = request.GET.get('patient_id')
        if patient_id and patient_id.isdecimal() and Patient.objects.filter(pk=patient_id, created_by=request.user).exists():
            initial['patient'] = patient_id
        form = AppointmentForm(user=request.user, initial=initial)
    return render(request, 'app/add_appointment.html', {
        'form': form,
        'has_patients': form.fields['patient'].queryset.exists(),
    })


@login_required
@require_POST
def update_appointment_status(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, created_by=request.user)
    status = request.POST.get('status')
    if appointment.status == 'scheduled' and status in ('completed', 'cancelled'):
        appointment.status = status
        appointment.save(update_fields=['status'])
        messages.success(request, f'Appointment marked {status}.')
    else:
        messages.error(request, 'This appointment cannot be updated.')
    return redirect('appointments')

@login_required
def upload_image(request):
    if request.method == 'POST':
        form = RetinaImageForm(request.POST, request.FILES)
        form.fields['patient'].queryset = Patient.objects.filter(created_by=request.user)
        if form.is_valid():
            if not dr_model.available:
                form.add_error(None, 'Image analysis is unavailable. Install a compatible model before uploading.')
            else:
                retina_image = form.save(commit=False)
                retina_image.analyzed_by = request.user
                try:
                    retina_image.save()
                    image_path = os.path.join(settings.MEDIA_ROOT, str(retina_image.image))
                    prediction = dr_model.predict(image_path)
                    retina_image.stage = prediction['class']
                    retina_image.confidence = prediction['confidence']
                    retina_image.save(update_fields=['stage', 'confidence'])
                except Exception:
                    logger.exception('Image analysis failed')
                    if retina_image.pk:
                        retina_image.image.delete(save=False)
                        retina_image.delete()
                    form.add_error(None, 'The image could not be analyzed. Please check the file and try again.')
                else:
                    messages.success(request, 'Image analyzed successfully.')
                    return redirect('result', pk=retina_image.id)
    else:
        initial = {}
        patient_id = request.GET.get('patient_id')
        if patient_id and patient_id.isdecimal() and Patient.objects.filter(pk=patient_id, created_by=request.user).exists():
            initial['patient'] = patient_id
        form = RetinaImageForm(initial=initial)
        form.fields['patient'].queryset = Patient.objects.filter(created_by=request.user)
    
    context = {
        'form': form,
        'model_available': dr_model.available,
    }
    return render(request, 'app/upload.html', context)

@login_required
def result(request, pk):
    retina_image = get_object_or_404(
        RetinaImage, pk=pk, analyzed_by=request.user, patient__created_by=request.user
    )
    
    # Get human-readable stage
    stage_display = dict(RetinaImage.STAGES).get(retina_image.stage)
    
    context = {
        'image': retina_image,
        'stage_display': stage_display,
        'confidence_percentage': round(retina_image.confidence * 100, 2) if retina_image.confidence else None,
    }
    return render(request, 'app/result.html', context)


def _private_image(file):
    content_type = mimetypes.guess_type(file.name)[0]
    if content_type not in ('image/jpeg', 'image/png', 'image/gif', 'image/webp'):
        raise Http404
    try:
        response = FileResponse(file.open('rb'), content_type=content_type)
    except (FileNotFoundError, ValueError):
        raise Http404 from None
    response['Cache-Control'] = 'private, no-store'
    response['Content-Disposition'] = 'inline'
    return response


@login_required
@never_cache
def profile_photo(request):
    if not request.user.profile_picture:
        raise Http404
    return _private_image(request.user.profile_picture)


@login_required
@never_cache
def retina_image_file(request, pk):
    image = get_object_or_404(
        RetinaImage, pk=pk, analyzed_by=request.user, patient__created_by=request.user
    )
    return _private_image(image.image)


def page_not_found(request, exception=None):
    return render(request, 'app/404.html', status=404)
