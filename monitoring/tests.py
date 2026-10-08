import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from classrooms.models import Classroom, ClassSession, Enrollment
from monitoring.models import ConsentRecord, EmotionEvent, SessionCheckIn


User = get_user_model()


class MonitoringPrivacyTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher',
            password='A-secure-password-42',
            full_name='Teacher One',
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username='student',
            password='A-secure-password-42',
            full_name='Student One',
            role=User.Role.STUDENT,
        )
        self.other_student = User.objects.create_user(
            username='other',
            password='A-secure-password-42',
            full_name='Other Student',
            role=User.Role.STUDENT,
        )
        self.classroom = Classroom.objects.create(
            name='Mathematics',
            teacher=self.teacher,
        )
        self.session = ClassSession.objects.create(classroom=self.classroom)
        Enrollment.objects.create(student=self.student, classroom=self.classroom)
        self.consent_url = reverse(
            'monitoring:toggle_consent',
            kwargs={'session_id': self.session.pk},
        )
        self.record_url = reverse('monitoring:record_emotion')
        self.checkin_url = reverse(
            'monitoring:session_checkin',
            kwargs={'session_id': self.session.pk},
        )

    def post_json(self, client, url, payload):
        return client.post(url, data=json.dumps(payload), content_type='application/json')

    def enable_consent(self, client=None):
        client = client or self.client
        return self.post_json(client, self.consent_url, {'active': True})

    def test_teacher_cannot_change_student_consent(self):
        self.client.force_login(self.teacher)

        response = self.post_json(self.client, self.consent_url, {'active': True})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ConsentRecord.objects.exists())

    def test_unenrolled_student_cannot_enable_consent(self):
        self.client.force_login(self.other_student)

        response = self.post_json(self.client, self.consent_url, {'active': True})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ConsentRecord.objects.exists())

    def test_student_can_enable_and_revoke_session_consent(self):
        self.client.force_login(self.student)

        enabled = self.enable_consent()
        disabled = self.post_json(self.client, self.consent_url, {'active': False})

        self.assertEqual(enabled.status_code, 200)
        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(ConsentRecord.objects.get(session=self.session).active)

    def test_student_can_revoke_consent_after_leaving_classroom(self):
        self.client.force_login(self.student)
        self.enable_consent()
        Enrollment.objects.filter(student=self.student, classroom=self.classroom).delete()

        response = self.post_json(self.client, self.consent_url, {'active': False})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ConsentRecord.objects.get(session=self.session).active)

    def test_consent_does_not_carry_into_another_session(self):
        self.client.force_login(self.student)
        self.enable_consent()
        next_session = ClassSession.objects.create(classroom=self.classroom)

        self.assertFalse(
            ConsentRecord.objects.filter(session=next_session, active=True).exists()
        )

    def test_signal_requires_active_session_consent(self):
        self.client.force_login(self.student)

        response = self.post_json(self.client, self.record_url, {
            'session_id': self.session.pk,
            'label': 'positive_expression',
            'confidence': 0.9,
        })

        self.assertEqual(response.status_code, 403)
        self.assertFalse(EmotionEvent.objects.exists())

    def test_low_confidence_and_no_face_are_distinguished(self):
        self.client.force_login(self.student)
        self.enable_consent()

        low_confidence = self.post_json(self.client, self.record_url, {
            'session_id': self.session.pk,
            'label': 'positive_expression',
            'confidence': 0.2,
        })
        no_face = self.post_json(self.client, self.record_url, {
            'session_id': self.session.pk,
            'label': 'no_face',
            'confidence': 0,
        })

        self.assertEqual(low_confidence.json()['stored'], 'low_confidence')
        self.assertEqual(no_face.json()['stored'], 'no_face')
        self.assertEqual(
            list(self.session.emotion_events.order_by('id').values_list('label', flat=True)),
            ['low_confidence', 'no_face'],
        )

    def test_invalid_signal_is_rejected(self):
        self.client.force_login(self.student)
        self.enable_consent()

        invalid_signals = [
            {'label': 'happy', 'confidence': 0.9},
            {'label': [], 'confidence': 0.9},
            {'label': 'positive_expression', 'confidence': float('nan')},
            {'label': 'positive_expression', 'confidence': 1.1},
            {'label': 'positive_expression', 'confidence': True},
        ]
        for signal in invalid_signals:
            with self.subTest(signal=signal):
                response = self.post_json(self.client, self.record_url, {
                    'session_id': self.session.pk,
                    **signal,
                })
                self.assertEqual(response.status_code, 400)
        self.assertFalse(EmotionEvent.objects.exists())

    def test_report_uses_aggregate_expression_language_and_limitations(self):
        EmotionEvent.objects.create(
            session=self.session,
            label='positive_expression',
            confidence=0.82,
        )
        self.client.force_login(self.teacher)

        response = self.client.get(reverse(
            'monitoring:session_report',
            kwargs={'pk': self.session.pk},
        ))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Facial Expression Estimate')
        self.assertContains(response, 'They do not prove how a person feels internally.')
        self.assertContains(response, 'Positive expression pattern')
        self.assertContains(response, '82% avg. confidence')
        self.assertNotContains(response, 'happy')
        self.assertNotContains(response, 'Student One')

    def test_signals_cannot_be_recorded_after_session_ends(self):
        self.client.force_login(self.student)
        self.enable_consent()
        self.session.is_active = False
        self.session.save(update_fields=['is_active'])

        response = self.post_json(self.client, self.record_url, {
            'session_id': self.session.pk,
            'label': 'positive_expression',
            'confidence': 0.9,
        })

        self.assertEqual(response.status_code, 409)
        self.assertFalse(EmotionEvent.objects.exists())

    def test_enrolled_student_can_submit_unlinked_self_report(self):
        self.client.force_login(self.student)

        response = self.client.post(self.checkin_url, {'response': 'another_example'})

        self.assertEqual(response.status_code, 302)
        checkin = SessionCheckIn.objects.get(session=self.session)
        self.assertEqual(checkin.response, 'another_example')
        self.assertNotIn('student', {field.name for field in SessionCheckIn._meta.fields})

    def test_checkin_rejects_teachers_unenrolled_users_and_invalid_choices(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(self.checkin_url, {'response': 'on_track'}).status_code, 403)

        self.client.force_login(self.other_student)
        self.assertEqual(self.client.post(self.checkin_url, {'response': 'on_track'}).status_code, 403)

        self.client.force_login(self.student)
        self.assertEqual(self.client.post(self.checkin_url, {'response': 'happy'}).status_code, 400)
        self.assertFalse(SessionCheckIn.objects.exists())

    def test_checkin_report_hides_small_or_imbalanced_categories(self):
        self.client.force_login(self.teacher)
        report_url = reverse('monitoring:session_report', kwargs={'pk': self.session.pk})
        for _ in range(5):
            SessionCheckIn.objects.create(session=self.session, response='on_track')

        visible_response = self.client.get(report_url)
        self.assertContains(visible_response, '5 responses')
        self.assertContains(visible_response, 'Following comfortably')

        SessionCheckIn.objects.create(session=self.session, response='need_pause')
        hidden_response = self.client.get(report_url)
        self.assertContains(hidden_response, 'No breakdown is shown yet.')
        self.assertNotContains(hidden_response, 'I need a short pause')