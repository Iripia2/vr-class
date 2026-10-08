from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .forms import ClassroomForm, JoinClassroomForm, LessonForm
from .models import Classroom, Enrollment, ClassSession
from monitoring.models import ConsentRecord
from monitoring.forms import SessionCheckInForm


@login_required
def dashboard(request):
    if request.user.is_teacher():
        classrooms = Classroom.objects.filter(teacher=request.user).order_by('-created_at')
        return render(request, 'classrooms/teacher_dashboard.html', {'classrooms': classrooms})

    enrollments = Enrollment.objects.filter(student=request.user).select_related('classroom')
    return render(request, 'classrooms/student_dashboard.html', {'enrollments': enrollments})


@login_required
def create_classroom(request):
    if not request.user.is_teacher():
        messages.error(request, 'Only teachers can create classrooms.')
        return redirect('classrooms:dashboard')

    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.teacher = request.user
            classroom.save()
            messages.success(request, f'"{classroom.name}" was created. Join code: {classroom.join_code}')
            return redirect('classrooms:classroom_detail', pk=classroom.pk)
    else:
        form = ClassroomForm()

    return render(request, 'classrooms/classroom_form.html', {'form': form})


@login_required
def join_classroom(request):
    if not request.user.is_student():
        messages.error(request, 'Only students can join classrooms.')
        return redirect('classrooms:dashboard')

    if request.method == 'POST':
        form = JoinClassroomForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['join_code'].strip().upper()
            try:
                classroom = Classroom.objects.get(join_code=code)
            except Classroom.DoesNotExist:
                messages.error(request, 'No classroom matches that join code.')
                return redirect('classrooms:dashboard')

            Enrollment.objects.get_or_create(student=request.user, classroom=classroom)
            messages.success(request, f'Joined {classroom.name}.')
            return redirect('classrooms:dashboard')

    return redirect('classrooms:dashboard')


@login_required
def classroom_detail(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    is_owner = classroom.teacher_id == request.user.id
    is_enrolled = Enrollment.objects.filter(classroom=classroom, student=request.user).exists()

    if not (is_owner or is_enrolled):
        messages.error(request, 'You do not have access to this classroom.')
        return redirect('classrooms:dashboard')

    lesson_form = LessonForm()
    active_session = classroom.sessions.filter(is_active=True).first()

    return render(request, 'classrooms/classroom_detail.html', {
        'classroom': classroom,
        'is_owner': is_owner,
        'lesson_form': lesson_form,
        'lessons': classroom.lessons.order_by('-created_at'),
        'students': Enrollment.objects.filter(classroom=classroom).select_related('student'),
        'active_session': active_session,
    })


@login_required
def add_lesson(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk, teacher=request.user)
    if request.method == 'POST':
        form = LessonForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.classroom = classroom
            lesson.save()
            messages.success(request, f'Lesson "{lesson.title}" added.')
    return redirect('classrooms:classroom_detail', pk=pk)


@login_required
def start_session(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk, teacher=request.user)
    lesson_id = request.POST.get('lesson_id') or None
    session = ClassSession.objects.create(classroom=classroom, lesson_id=lesson_id)
    return redirect('classrooms:virtual_classroom', pk=session.pk)


@login_required
def end_session(request, pk):
    from django.utils import timezone
    session = get_object_or_404(ClassSession, pk=pk, classroom__teacher=request.user)
    session.is_active = False
    session.ended_at = timezone.now()
    session.save()
    return redirect('classrooms:classroom_detail', pk=session.classroom_id)


@login_required
def virtual_classroom(request, pk):
    session = get_object_or_404(ClassSession, pk=pk)
    classroom = session.classroom
    is_owner = classroom.teacher_id == request.user.id
    is_enrolled = Enrollment.objects.filter(classroom=classroom, student=request.user).exists()

    if not (is_owner or is_enrolled):
        messages.error(request, 'You do not have access to this session.')
        return redirect('classrooms:dashboard')

    consent = None
    if request.user.is_student():
        consent, _ = ConsentRecord.objects.get_or_create(
            student=request.user,
            classroom=classroom,
            session=session,
        )

    return render(request, 'classrooms/virtual_classroom.html', {
        'session': session,
        'classroom': classroom,
        'is_owner': is_owner,
        'consent': consent,
        'checkin_form': SessionCheckInForm() if request.user.is_student() else None,
    })
