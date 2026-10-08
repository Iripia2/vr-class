from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from classrooms.models import ClassSession, Classroom, Enrollment


User = get_user_model()
TEST_PASSWORD = 'Sufficiently-Long-Classroom-Password-42!'


class ClassroomDefenseWorkflowTests(TestCase):
    def register(self, client, username, role):
        return client.post(reverse('accounts:register'), {
            'full_name': f'{role.title()} User',
            'email': f'{username}@example.test',
            'username': username,
            'role': role,
            'password1': TEST_PASSWORD,
            'password2': TEST_PASSWORD,
        })

    def test_teacher_student_classroom_session_report_workflow(self):
        teacher_client = self.client
        teacher_response = self.register(teacher_client, 'teacher', User.Role.TEACHER)
        self.assertRedirects(teacher_response, reverse('classrooms:dashboard'))
        teacher = User.objects.get(username='teacher')

        create_response = teacher_client.post(reverse('classrooms:create_classroom'), {
            'name': 'Virtual Mathematics',
            'subject': 'Mathematics',
        })
        self.assertEqual(create_response.status_code, 302)
        classroom = Classroom.objects.get(teacher=teacher)

        lesson_response = teacher_client.post(
            reverse('classrooms:add_lesson', kwargs={'pk': classroom.pk}),
            {'title': 'Fractions', 'description': 'Equivalent fractions'},
        )
        self.assertEqual(lesson_response.status_code, 302)
        lesson = classroom.lessons.get(title='Fractions')

        student_client = type(self.client)()
        student_response = self.register(student_client, 'student', User.Role.STUDENT)
        self.assertRedirects(student_response, reverse('classrooms:dashboard'))
        student = User.objects.get(username='student')
        student_client.post(reverse('classrooms:join_classroom'), {
            'join_code': classroom.join_code,
        })
        self.assertTrue(Enrollment.objects.filter(student=student, classroom=classroom).exists())

        start_response = teacher_client.post(
            reverse('classrooms:start_session', kwargs={'pk': classroom.pk}),
            {'lesson_id': lesson.pk},
        )
        session = ClassSession.objects.get(classroom=classroom, is_active=True)
        self.assertRedirects(
            start_response,
            reverse('classrooms:virtual_classroom', kwargs={'pk': session.pk}),
        )

        room_response = student_client.get(
            reverse('classrooms:virtual_classroom', kwargs={'pk': session.pk})
        )
        self.assertEqual(room_response.status_code, 200)
        self.assertContains(room_response, 'Continue Without Monitoring')
        self.assertContains(room_response, 'Review Privacy Details')
        self.assertContains(room_response, 'I Consent &amp; Enable Monitoring')
        self.assertContains(
            room_response,
            'Expression estimates describe observable facial-expression patterns only.',
        )
        self.assertContains(room_response, 'Optional class check-in')
        self.assertContains(room_response, 'Share check-in')

        report_response = teacher_client.get(
            reverse('monitoring:session_report', kwargs={'pk': session.pk})
        )
        self.assertEqual(report_response.status_code, 200)
        self.assertContains(report_response, 'Class-level report')