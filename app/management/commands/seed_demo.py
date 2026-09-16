import secrets
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from app.models import Appointment, Patient, User


DEMO_EMAIL = 'demo@drvision.example'
DEMO_PATIENTS = [
    ('Amina', 'Bennani', 'F', 1984, 'Routine follow-up'),
    ('Youssef', 'El Idrissi', 'M', 1976, 'Medication review'),
    ('Nadia', 'Mansouri', 'F', 1990, 'Annual examination'),
    ('Karim', 'Alaoui', 'M', 1968, 'Blood pressure review'),
    ('Salma', 'Haddad', 'F', 1987, 'Lab results review'),
    ('Omar', 'Amrani', 'M', 1972, 'Diabetes follow-up'),
    ('Leila', 'Fassi', 'F', 1995, 'Routine consultation'),
    ('Rachid', 'Naciri', 'M', 1981, 'Treatment discussion'),
    ('Meryem', 'Ziani', 'F', 1979, 'Wellness visit'),
    ('Hassan', 'Khalil', 'M', 1992, 'Follow-up visit'),
]


class Command(BaseCommand):
    help = 'Create fictional patients and appointments for local screenshots.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Demo data may only be created when DJANGO_DEBUG=1.')

        user, created = User.objects.get_or_create(
            username='demo_clinic',
            defaults={
                'email': DEMO_EMAIL,
                'first_name': 'Maya',
                'last_name': 'Chen',
                'hospital': 'Sample Clinic',
                'license_number': 'DEMO-ONLY',
            },
        )
        if not created and user.email != DEMO_EMAIL:
            raise CommandError('The demo_clinic username belongs to another account.')

        password = secrets.token_urlsafe(16)
        user.set_password(password)
        user.save(update_fields=['password'])

        patients = []
        for number, (first_name, last_name, gender, birth_year, reason) in enumerate(DEMO_PATIENTS, 1):
            patient, patient_created = Patient.objects.get_or_create(
                patient_id=f'DEMO-{number:03d}',
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'date_of_birth': date(birth_year, number, 12),
                    'gender': gender,
                    'phone': f'000-000-{number:04d}',
                    'email': f'demo.patient{number}@example.test',
                    'medical_history': 'Fictional sample record for screenshots.',
                    'created_by': user,
                },
            )
            if not patient_created and patient.created_by_id != user.pk:
                raise CommandError(f'{patient.patient_id} belongs to another account.')
            patients.append((patient, reason))

        offsets_and_statuses = [
            (1, 'scheduled'), (2, 'scheduled'), (3, 'scheduled'),
            (5, 'scheduled'), (7, 'scheduled'), (-2, 'completed'),
            (-6, 'cancelled'),
        ]
        today = timezone.localdate()
        for index, (offset, status) in enumerate(offsets_and_statuses):
            patient, reason = patients[index]
            scheduled_at = timezone.make_aware(
                datetime.combine(today + timedelta(days=offset), time(9 + index % 4, 30))
            )
            Appointment.objects.update_or_create(
                patient=patient,
                created_by=user,
                reason=reason,
                defaults={'scheduled_at': scheduled_at, 'status': status},
            )

        self.stdout.write(self.style.SUCCESS('Demo data ready: 10 fictional patients and 7 appointments.'))
        self.stdout.write('Username: demo_clinic')
        self.stdout.write(f'Temporary password: {password}')
        self.stdout.write('Running this command again rotates the password and refreshes appointment dates.')
