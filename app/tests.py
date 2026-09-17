from datetime import timedelta
from io import BytesIO, StringIO
from html.parser import HTMLParser
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone
from PIL import Image

from .forms import PatientForm, UserRegisterForm
from .models import Appointment, Patient, RetinaImage


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.links.append(href)


class PageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='doctor', password='pass12345')
        cls.patient = Patient.objects.create(
            patient_id='P-001', first_name='Ada', last_name='Smith',
            date_of_birth='1980-01-01', gender='F', phone='123456789', created_by=cls.user,
        )
        cls.image = RetinaImage.objects.create(
            patient=cls.patient, image='retina_images/example.png',
            stage=1, confidence=0.8, analyzed_by=cls.user,
        )

    def test_public_pages_render_metadata_and_favicon(self):
        for name in ('login', 'register'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'name="description"')
                self.assertContains(response, 'favicon.svg')

    def test_authenticated_pages_render(self):
        self.client.force_login(self.user)
        urls = (
            reverse('dashboard'), reverse('history'), reverse('add_patient'),
            reverse('upload'), reverse('profile'), reverse('appointments'),
            reverse('add_appointment'), reverse('edit_patient', args=[self.patient.pk]),
            reverse('patient_detail', args=[self.patient.pk]),
            reverse('result', args=[self.image.pk]),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'name="description"')
                self.assertContains(response, 'DR Vision')

    def test_page_links_resolve(self):
        self.client.force_login(self.user)
        urls = (
            reverse('dashboard'), reverse('history'), reverse('add_patient'),
            reverse('upload'), reverse('profile'), reverse('appointments'),
            reverse('add_appointment'), reverse('edit_patient', args=[self.patient.pk]),
            reverse('patient_detail', args=[self.patient.pk]),
            reverse('result', args=[self.image.pk]),
        )
        for url in urls:
            parser = LinkParser()
            parser.feed(self.client.get(url).content.decode())
            for link in parser.links:
                with self.subTest(page=url, link=link):
                    self.assertNotEqual(link, '#')
                    self.assertTrue(link.startswith('/'))
                    resolve(urlsplit(link).path)

    def test_custom_404(self):
        response = self.client.get('/missing-page/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Page not found', status_code=404)

    @override_settings(DEBUG=False)
    def test_custom_404_without_debug(self):
        response = self.client.get('/missing-page/')
        self.assertContains(response, 'Page not found', status_code=404)

    def test_upload_patient_prefill_and_owner_validation(self):
        other = get_user_model().objects.create_user(username='other', password='pass12345')
        foreign_patient = Patient.objects.create(
            patient_id='P-002', first_name='Bob', last_name='Jones',
            date_of_birth='1980-01-01', gender='M', phone='123456789', created_by=other,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('upload') + f'?patient_id={self.patient.pk}')
        self.assertEqual(str(response.context['form']['patient'].value()), str(self.patient.pk))
        response = self.client.get(reverse('upload') + '?patient_id=not-a-number')
        self.assertEqual(response.status_code, 200)

        image = Image.new('RGB', (4, 4), 'white')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        upload = SimpleUploadedFile('scan.png', buffer.getvalue(), content_type='image/png')
        response = self.client.post(reverse('upload'), {'patient': foreign_patient.pk, 'image': upload})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select a valid choice')
        self.assertEqual(RetinaImage.objects.count(), 1)

        upload = SimpleUploadedFile('scan.png', buffer.getvalue(), content_type='image/png')
        with patch('app.views.dr_model') as model:
            model.available = False
            response = self.client.post(reverse('upload'), {'patient': self.patient.pk, 'image': upload})
        self.assertContains(response, 'Image analysis is unavailable')
        self.assertEqual(RetinaImage.objects.count(), 1)

    def test_successful_analysis_shows_result(self):
        self.client.force_login(self.user)
        image = Image.new('RGB', (4, 4), 'white')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        upload = SimpleUploadedFile('scan.png', buffer.getvalue(), content_type='image/png')
        storage = {
            'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        }
        with override_settings(STORAGES=storage):
            with patch('app.views.dr_model') as model:
                model.available = True
                def predict(image_file):
                    self.assertEqual(image_file.read(8), b'\x89PNG\r\n\x1a\n')
                    return {'class': 2, 'confidence': 0.83}

                model.predict.side_effect = predict
                response = self.client.post(reverse('upload'), {'patient': self.patient.pk, 'image': upload})
            scan = RetinaImage.objects.get(stage=2)
            self.assertRedirects(response, reverse('result', args=[scan.pk]))
            self.assertAlmostEqual(scan.confidence, 0.83)
            image_response = self.client.get(reverse('retina_image_file', args=[scan.pk]))
            self.assertEqual(b''.join(image_response.streaming_content), buffer.getvalue())

    def test_login_errors_visible(self):
        response = self.client.post(reverse('login'), {'username': 'doctor', 'password': 'wrong'})
        self.assertContains(response, 'Please enter a correct username and password')

    def test_failed_analysis_cleans_up_upload(self):
        self.client.force_login(self.user)
        image = Image.new('RGB', (4, 4), 'white')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        upload = SimpleUploadedFile('scan.png', buffer.getvalue(), content_type='image/png')
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            with patch('app.views.dr_model') as model:
                model.available = True
                model.predict.side_effect = ValueError('bad scan')
                response = self.client.post(reverse('upload'), {'patient': self.patient.pk, 'image': upload})
            self.assertContains(response, 'The image could not be analyzed')
            self.assertEqual(RetinaImage.objects.count(), 1)


class FormTests(TestCase):
    def test_future_birth_date_is_rejected(self):
        form = PatientForm(data={
            'patient_id': 'P-003', 'first_name': 'Ada', 'last_name': 'Smith',
            'date_of_birth': (timezone.localdate() + timedelta(days=1)).isoformat(),
            'gender': 'F', 'phone': '123456789',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('Date of birth cannot be in the future.', form.errors['date_of_birth'])

    def test_registration_requires_names(self):
        form = UserRegisterForm(data={
            'username': 'newdoctor', 'email': 'doctor@example.com',
            'hospital': 'General Hospital', 'license_number': '123',
            'phone_number': '123456789', 'password1': 'longsecurepassword123',
            'password2': 'longsecurepassword123',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)
        self.assertIn('last_name', form.errors)


class DoctorWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = get_user_model().objects.create_user(username='doctor_a', password='pass12345')
        cls.other_doctor = get_user_model().objects.create_user(username='doctor_b', password='pass12345')
        cls.patient = Patient.objects.create(
            patient_id='A-001', first_name='Ada', last_name='Smith',
            date_of_birth='1980-01-01', gender='F', phone='111111111', created_by=cls.doctor,
        )
        cls.other_patient = Patient.objects.create(
            patient_id='B-001', first_name='Bob', last_name='Jones',
            date_of_birth='1980-01-01', gender='M', phone='222222222', created_by=cls.other_doctor,
        )

    def setUp(self):
        self.client.force_login(self.doctor)

    def test_patient_search_only_shows_own_records(self):
        response = self.client.get(reverse('history'), {'q': 'Ada Smith'})
        self.assertContains(response, 'Ada Smith')
        self.assertNotContains(response, 'Bob Jones')
        response = self.client.get(reverse('history'), {'q': 'B-001'})
        self.assertContains(response, 'No patients match your search')
        response = self.client.get(reverse('history'), {'q': "' OR 1=1 --"})
        self.assertContains(response, 'No patients match your search')
        self.assertNotContains(response, 'Bob Jones')

    def test_patient_edit_is_scoped_and_validated(self):
        self.assertEqual(self.client.get(reverse('edit_patient', args=[self.other_patient.pk])).status_code, 404)
        url = reverse('edit_patient', args=[self.patient.pk])
        data = {
            'patient_id': 'A-001', 'first_name': 'Ada', 'last_name': 'Taylor',
            'date_of_birth': '1980-01-01', 'gender': 'F', 'phone': '111111111',
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('patient_detail', args=[self.patient.pk]))
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.last_name, 'Taylor')
        data['date_of_birth'] = (timezone.localdate() + timedelta(days=1)).isoformat()
        response = self.client.post(url, data)
        self.assertContains(response, 'Date of birth cannot be in the future')

    def test_appointment_creation_prefill_and_validation(self):
        url = reverse('add_appointment')
        response = self.client.get(url, {'patient_id': self.patient.pk})
        self.assertEqual(str(response.context['form']['patient'].value()), str(self.patient.pk))

        future = timezone.localtime(timezone.now() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
        data = {'patient': self.other_patient.pk, 'scheduled_at': future, 'reason': 'Follow-up'}
        self.assertContains(self.client.post(url, data), 'Select a valid choice')
        self.assertEqual(Appointment.objects.count(), 0)

        data['patient'] = self.patient.pk
        data['scheduled_at'] = timezone.localtime(timezone.now() - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
        self.assertContains(self.client.post(url, data), 'Choose a future date and time')
        self.assertEqual(Appointment.objects.count(), 0)

        data['scheduled_at'] = future
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('appointments'))
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.created_by, self.doctor)
        self.assertEqual(appointment.patient, self.patient)
        self.assertContains(self.client.get(reverse('dashboard')), 'Follow-up')

        response = self.client.post(url, data)
        self.assertContains(response, 'You already have an appointment at this time')
        self.assertEqual(Appointment.objects.count(), 1)

    def test_appointment_status_requires_owner_and_post(self):
        appointment = Appointment.objects.create(
            patient=self.patient, created_by=self.doctor,
            scheduled_at=timezone.now() + timedelta(days=2), reason='Review',
        )
        foreign = Appointment.objects.create(
            patient=self.other_patient, created_by=self.other_doctor,
            scheduled_at=timezone.now() + timedelta(days=2), reason='Other',
        )
        url = reverse('appointment_status', args=[appointment.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(reverse('appointment_status', args=[foreign.pk]), {'status': 'completed'}).status_code, 404)
        self.assertRedirects(self.client.post(url, {'status': 'completed'}), reverse('appointments'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'completed')
        self.assertRedirects(self.client.post(url, {'status': 'cancelled'}), reverse('appointments'))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'completed')


class SecurityTests(TestCase):
    @override_settings(DEBUG=False, ALLOW_PUBLIC_REGISTRATION=False)
    def test_public_registration_is_closed_outside_development(self):
        self.assertEqual(self.client.get(reverse('register')).status_code, 404)
        self.assertNotContains(self.client.get(reverse('login')), 'Create an account')

    def test_private_images_require_the_owner(self):
        owner = get_user_model().objects.create_user(username='owner', password='pass12345')
        other = get_user_model().objects.create_user(username='stranger', password='pass12345')
        patient = Patient.objects.create(
            patient_id='PRIVATE-001', first_name='Sample', last_name='Patient',
            date_of_birth='1980-01-01', gender='F', phone='000000000', created_by=owner,
        )
        image = Image.new('RGB', (4, 4), 'white')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            scan = RetinaImage.objects.create(
                patient=patient, analyzed_by=owner, stage=0, confidence=0.8,
                image=SimpleUploadedFile('scan.png', buffer.getvalue(), content_type='image/png'),
            )
            url = reverse('retina_image_file', args=[scan.pk])
            self.assertEqual(self.client.get(url).status_code, 302)
            self.client.force_login(other)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.client.force_login(owner)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertEqual(b''.join(response.streaming_content), buffer.getvalue())
            self.assertEqual(self.client.get('/media/' + scan.image.name).status_code, 404)

    def test_profile_photo_is_private_and_can_be_removed(self):
        user = get_user_model().objects.create_user(
            username='photo_owner', email='photo@example.test', password='pass12345'
        )
        image = Image.new('RGB', (4, 4), 'white')
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            user.profile_picture.save(
                'avatar.png', SimpleUploadedFile('avatar.png', buffer.getvalue(), content_type='image/png')
            )
            self.assertEqual(self.client.get(reverse('profile_photo')).status_code, 302)
            self.client.force_login(user)
            response = self.client.get(reverse('profile_photo'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), buffer.getvalue())
            self.assertNotContains(self.client.get(reverse('profile')), '/media/profiles/')
            response = self.client.post(reverse('profile'), {
                'username': user.username, 'email': user.email, 'remove_photo': 'on',
            })
            self.assertRedirects(response, reverse('profile'))
            user.refresh_from_db()
            self.assertFalse(user.profile_picture)
            self.assertEqual(self.client.get(reverse('profile_photo')).status_code, 404)

    def test_status_change_requires_csrf_token(self):
        doctor = get_user_model().objects.create_user(username='doctor_csrf', password='pass12345')
        patient = Patient.objects.create(
            patient_id='CSRF-001', first_name='Sample', last_name='Patient',
            date_of_birth='1980-01-01', gender='F', phone='000000000', created_by=doctor,
        )
        appointment = Appointment.objects.create(
            patient=patient, created_by=doctor,
            scheduled_at=timezone.now() + timedelta(days=1), reason='Review',
        )
        client = Client(enforce_csrf_checks=True)
        client.force_login(doctor)
        response = client.post(reverse('appointment_status', args=[appointment.pk]), {'status': 'completed'})
        self.assertEqual(response.status_code, 403)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'scheduled')


class DemoDataTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_is_fictional_and_repeatable(self):
        text_output = StringIO()
        call_command('seed_demo', stdout=text_output)
        self.assertIn('Temporary password:', text_output.getvalue())
        self.assertEqual(Patient.objects.filter(patient_id__startswith='DEMO-').count(), 10)
        self.assertEqual(Appointment.objects.count(), 7)
        self.assertEqual(RetinaImage.objects.count(), 0)
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Patient.objects.filter(patient_id__startswith='DEMO-').count(), 10)
        self.assertEqual(Appointment.objects.count(), 7)

    @override_settings(DEBUG=True)
    def test_seed_existing_account_without_changing_login(self):
        doctor = get_user_model().objects.create_user(username='doctor', password='original-password')
        call_command('seed_demo', username='doctor', stdout=StringIO())
        call_command('seed_demo', username='doctor', stdout=StringIO())

        doctor.refresh_from_db()
        self.assertTrue(doctor.check_password('original-password'))
        self.assertEqual(Patient.objects.filter(created_by=doctor).count(), 10)
        self.assertEqual(Appointment.objects.filter(created_by=doctor).count(), 7)
        self.assertEqual(Patient.objects.filter(patient_id__startswith='DEMO-U').count(), 10)

        self.client.force_login(doctor)
        self.assertContains(self.client.get(reverse('dashboard')), '10')
        self.assertEqual(self.client.get(reverse('appointments')).status_code, 200)

    @override_settings(DEBUG=True)
    def test_seed_existing_account_requires_a_real_user(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo', username='missing-doctor', stdout=StringIO())

    @override_settings(DEBUG=False)
    def test_seed_refuses_production_mode(self):
        with self.assertRaises(CommandError):
            call_command('seed_demo', stdout=StringIO())
