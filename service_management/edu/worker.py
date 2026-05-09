import logging
from django.utils import timezone
from django.db import transaction
from .models import EduProfile, AttendanceRecord, StaffWorkSession, LiveSchoolStatus, TimetableSlot
from sterling_core.models import SterlingUser, Unit
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

STUDENT_BUFFER = []

def process_edu_tap(packet):
    """
    Role-based state machine for edu app.
    Processes tap events for students and staff.
    """
    try:
        user_id = packet.get('user_id')
        unit_id = packet.get('unit_id')
        
        if not all([user_id, unit_id]):
            logger.error("Invalid packet: missing user_id or unit_id")
            return False
        
        user = SterlingUser.objects.get(id=user_id)
        unit = Unit.objects.get(id=unit_id)
        timestamp = timezone.now()
        
        # Get or create EduProfile
        edu_profile, _ = EduProfile.objects.get_or_create(
            user=user,
            defaults={'role_type': 'STUDENT'}
        )
        
        if edu_profile.role_type == 'STUDENT':
            _handle_student_tap(user, unit, timestamp, packet)
        else:
            _handle_staff_tap(user, unit, timestamp, edu_profile)
        
        # Broadcast update via WebSocket
        _broadcast_update(user, unit, edu_profile, timestamp)
        
        return True
        
    except SterlingUser.DoesNotExist:
        logger.error("User not found: %s", user_id)
        return False
    except Unit.DoesNotExist:
        logger.error("Unit not found: %s", unit_id)
        return False
    except Exception as e:
        logger.error("Error processing edu tap: %s", e)
        return False

def _broadcast_update(user, unit, edu_profile, timestamp):
    """Broadcast live update via WebSocket."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'edu_dashboard',
            {
                'type': 'live_update',
                'data': {
                    'type': 'live_update',
                    'name': user.username,
                    'role': edu_profile.get_role_type_display(),
                    'status': LiveSchoolStatus.objects.get(user=user).state if LiveSchoolStatus.objects.filter(user=user).exists() else 'Unknown',
                    'time': timestamp.strftime('%H:%M:%S'),
                    'location': unit.name
                }
            }
        )
    except Exception as e:
        logger.error("Failed to broadcast update: %s", e)

def _handle_student_tap(user, unit, timestamp, packet):
    """Handle student attendance tap with bulk buffering."""
    from django.conf import settings
    
    # Get or create attendance record for today
    record, created = AttendanceRecord.objects.get_or_create(
        user=user,
        date=timezone.now().date(),
        defaults={
            'unit': unit,
            'first_tap': timestamp,
            'last_tap': timestamp,
            'status': 'PRESENT'
        }
    )
    
    if not created:
        record.last_tap = timestamp
        
        # Check if late
        if not record.metadata.get('checked_late'):
            school_start = getattr(settings, 'SCHOOL_START_TIME', '08:00')
            from datetime import datetime
            start_time = datetime.strptime(school_start, '%H:%M').time()
            if timestamp.time() > start_time:
                record.status = 'LATE'
            record.metadata['checked_late'] = True
        
        # Update metadata with location and time
        if 'taps' not in record.metadata:
            record.metadata['taps'] = []
        
        record.metadata['taps'].append({
            'location': unit.name,
            'time': str(timestamp)
        })
        record.save()
    else:
        # Add to bulk buffer
        STUDENT_BUFFER.append(record)
        if len(STUDENT_BUFFER) >= 50:
            AttendanceRecord.objects.bulk_create(STUDENT_BUFFER)
            STUDENT_BUFFER.clear()
            logger.info("Bulk created 50 student attendance records")

def _handle_staff_tap(user, unit, timestamp, edu_profile):
    """Handle staff tap with state machine: OUT -> IN -> BREAK -> IN -> OUT."""
    live_status, _ = LiveSchoolStatus.objects.get_or_create(
        user=user,
        defaults={'state': 'OUT', 'current_location': unit.name}
    )
    
    current_state = live_status.state
    
    if current_state == 'OUT':
        # Clock in
        session = StaffWorkSession.objects.create(
            user=user,
            unit=unit,
            clock_in=timestamp,
            current_status='IN'
        )
        live_status.state = 'IN'
        live_status.current_location = unit.name
        live_status.save()
        logger.info("Staff clock in: %s at %s", user.username, unit.name)
        
    elif current_state == 'IN':
        # Check if on break or clocking out
        session = StaffWorkSession.objects.filter(
            user=user,
            unit=unit,
            current_status='IN'
        ).order_by('-clock_in').first()
        
        if session:
            # Check timetable for break vs clock out logic
            timetable = TimetableSlot.objects.filter(
                teacher=user,
                day_of_week=timezone.now().strftime('%a').upper()[:3]
            ).first()
            
            if timetable and timestamp.time() >= timetable.end_time:
                # Clock out
                session.clock_out = timestamp
                session.current_status = 'OUT'
                session.save()
                live_status.state = 'OUT'
                logger.info("Staff clock out: %s", user.username)
            else:
                # Start break
                session.current_status = 'BREAK'
                session.save()
                live_status.state = 'ON_BREAK'
                logger.info("Staff break start: %s", user.username)
        
        live_status.current_location = unit.name
        live_status.save()
        
    elif current_state == 'ON_BREAK':
        # End break
        session = StaffWorkSession.objects.filter(
            user=user,
            unit=unit,
            current_status='BREAK'
        ).order_by('-clock_in').first()
        
        if session:
            session.current_status = 'IN'
            session.save()
            live_status.state = 'IN'
            logger.info("Staff break end: %s", user.username)
        
        live_status.current_location = unit.name
        live_status.save()
    
    # Enrichment: Log classroom if teacher is in class
    if edu_profile.role_type == 'TEACHER':
        timetable = TimetableSlot.objects.filter(
            teacher=user,
            day_of_week=timezone.now().strftime('%a').upper()[:3]
        ).first()
        
        if timetable:
            record, _ = AttendanceRecord.objects.get_or_create(
                user=user,
                date=timezone.now().date(),
                defaults={
                    'unit': unit,
                    'first_tap': timestamp,
                    'status': 'IN_SHIFT'
                }
            )
            if 'timetable' not in record.metadata:
                record.metadata['timetable'] = []
            record.metadata['timetable'].append({
                'classroom': timetable.classroom,
                'subject': timetable.subject,
                'time': str(timestamp)
            })
            record.save()
