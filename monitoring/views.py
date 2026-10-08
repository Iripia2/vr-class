import json
import math

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from classrooms.models import Classroom, ClassSession, Enrollment
from .forms import SessionCheckInForm
from .models import ConsentRecord, EmotionEvent, SessionCheckIn

VALID_LABELS = {choice[0] for choice in EmotionEvent.LABEL_CHOICES}
CONFIDENCE_THRESHOLD = 0.4
LEGACY_LABELS = {
    'happy': 'positive_expression',
    'neutral': 'neutral_steady',
    'sad': 'negative_expression',
    'angry': 'negative_expression',
    'fearful': 'negative_expression',
    'surprised': 'surprise_like',
    'disgusted': 'negative_expression',
    'unknown': 'low_confidence',
}


@login_required
@require_POST
def toggle_consent(request, session_id):
    if not request.user.is_student():
        return JsonResponse({'error': 'student account required'}, status=403)

    try:
        payload = json.loads(request.body)
    except (TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'invalid payload'}, status=400)

    active = payload.get('active') if isinstance(payload, dict) else None
    if type(active) is not bool:
        return JsonResponse({'error': 'active must be true or false'}, status=400)

    session = get_object_or_404(ClassSession, pk=session_id)
    classroom = session.classroom
    enrolled = Enrollment.objects.filter(classroom=classroom, student=request.user).exists()
    existing_consent = ConsentRecord.objects.filter(
        student=request.user,
        session=session,
    ).first()
    if active and not enrolled:
        return JsonResponse({'error': 'not enrolled in this classroom'}, status=403)
    if not active and not enrolled and existing_consent is None:
        return JsonResponse({'error': 'not enrolled in this classroom'}, status=403)
    if active and not session.is_active:
        return JsonResponse({'error': 'session is no longer active'}, status=409)

    consent = existing_consent
    if consent is None:
        consent = ConsentRecord.objects.create(
            student=request.user,
            classroom=classroom,
            session=session,
        )
    consent.active = active
    consent.save()
    return JsonResponse({'active': consent.active})


@login_required
@csrf_protect
@require_POST
def record_emotion(request):
    """
    Receives a single client-side detection result (label + confidence) and
    stores only that label — never an image or video frame. Requires the
    student to currently have consent switched on for the classroom.
    """
    try:
        payload = json.loads(request.body)
        session_id = int(payload['session_id'])
        label = payload.get('label', 'low_confidence')
        raw_confidence = payload.get('confidence', 0.0)
        if isinstance(raw_confidence, bool):
            raise ValueError
        confidence = float(raw_confidence)
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'invalid payload'}, status=400)

    if request.user.is_student() is False:
        return JsonResponse({'error': 'student account required'}, status=403)

    if (
        not isinstance(label, str)
        or not math.isfinite(confidence)
        or not 0 <= confidence <= 1
        or label not in VALID_LABELS
    ):
        return JsonResponse({'error': 'invalid signal'}, status=400)

    session = get_object_or_404(ClassSession, pk=session_id)
    if not session.is_active:
        return JsonResponse({'error': 'session is no longer active'}, status=409)

    if not Enrollment.objects.filter(classroom=session.classroom, student=request.user).exists():
        return JsonResponse({'error': 'not enrolled in this classroom'}, status=403)

    consent = ConsentRecord.objects.filter(
        student=request.user, session=session, active=True
    ).first()
    if not consent:
        return JsonResponse({'error': 'consent is not active'}, status=403)

    if label != 'no_face' and confidence < CONFIDENCE_THRESHOLD:
        label = 'low_confidence'

    EmotionEvent.objects.create(session=session, label=label, confidence=confidence)
    return JsonResponse({'stored': label})


@login_required
@require_POST
def submit_session_checkin(request, session_id):
    if not request.user.is_student():
        return JsonResponse({'error': 'student account required'}, status=403)

    session = get_object_or_404(ClassSession, pk=session_id)
    if not session.is_active:
        return JsonResponse({'error': 'session is no longer active'}, status=409)
    if not Enrollment.objects.filter(classroom=session.classroom, student=request.user).exists():
        return JsonResponse({'error': 'not enrolled in this classroom'}, status=403)

    form = SessionCheckInForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': 'choose a valid check-in response'}, status=400)

    check_in = form.save(commit=False)
    check_in.session = session
    check_in.save()
    messages.success(request, 'Your optional check-in was recorded without your account details.')
    return redirect('classrooms:virtual_classroom', pk=session.pk)


@login_required
def session_report(request, pk):
    session = get_object_or_404(ClassSession, pk=pk, classroom__teacher=request.user)

    display_labels = dict(EmotionEvent.LABEL_CHOICES)
    counts = {label: 0 for label in display_labels.values()}
    confidence_totals = {label: 0.0 for label in display_labels.values()}
    events = session.emotion_events.values('label').annotate(
        total=Count('id'),
        average_confidence=Avg('confidence'),
    )
    for event in events:
        label = LEGACY_LABELS.get(event['label'], event['label'])
        if label in display_labels:
            display_label = display_labels[label]
            counts[display_label] += event['total']
            confidence_totals[display_label] += (
                event['average_confidence'] or 0.0
            ) * event['total']

    total = sum(counts.values())
    signal_rows = [
        {
            'label': label,
            'count': count,
            'confidence': round(confidence_totals[label] / count * 100) if count else None,
        }
        for label, count in counts.items()
    ]
    opted_in = ConsentRecord.objects.filter(session=session, active=True).count()
    enrolled = Enrollment.objects.filter(classroom=session.classroom).count()
    checkin_rows = list(
        session.check_ins.values('response').annotate(total=Count('id')).order_by('response')
    )
    checkin_total = sum(row['total'] for row in checkin_rows)
    checkin_breakdown_visible = (
        checkin_total >= 5
        and all(row['total'] >= 5 for row in checkin_rows)
    )
    checkin_labels = dict(SessionCheckIn.Response.choices)
    checkin_rows = [
        {'label': checkin_labels[row['response']], 'count': row['total']}
        for row in checkin_rows
    ] if checkin_breakdown_visible else []

    return render(request, 'monitoring/report.html', {
        'session': session,
        'counts': counts,
        'signal_rows': signal_rows,
        'total': total,
        'opted_in': opted_in,
        'enrolled': enrolled,
        'checkin_total': checkin_total if checkin_breakdown_visible else None,
        'checkin_rows': checkin_rows,
        'checkin_breakdown_visible': checkin_breakdown_visible,
    })
