import logging
from django.utils import timezone
from django.db import transaction
from .models import WorkSession, DailyBreakLog, UserLiveStatus, ShiftTemplate
from sterling_core.models import SterlingUser

logger = logging.getLogger(__name__)

def process_fnb_tap(packet):
    """
    Dynamic state machine for F&B shift management.
    Processes tap events and transitions between OUT/IN/BREAK states.
    """
    try:
        user_id = packet.get('user_id')
        unit_id = packet.get('unit_id')
        
        if not all([user_id, unit_id]):
            logger.error("Invalid packet: missing user_id or unit_id")
            return False
        
        user = SterlingUser.objects.get(id=user_id)
        timestamp = timezone.now()
        
        with transaction.atomic():
            live_status, _ = UserLiveStatus.objects.get_or_create(
                user=user,
                defaults={'current_state': 'OUT', 'last_unit_id': unit_id}
            )
            
            current_state = live_status.current_state
            
            if current_state == 'OUT':
                _handle_clock_in(user, unit_id, timestamp, live_status)
            elif current_state == 'IN':
                _handle_break_or_clock_out(user, unit_id, timestamp, live_status)
            elif current_state == 'BREAK':
                _handle_break_end(user, unit_id, timestamp, live_status)
            
            live_status.last_tap = timestamp
            live_status.last_unit_id = unit_id
            live_status.save()
        
        return True
        
    except SterlingUser.DoesNotExist:
        logger.error("User not found: %s", user_id)
        return False
    except Exception as e:
        logger.error("Error processing tap: %s", e)
        return False

def _handle_clock_in(user, unit_id, timestamp, live_status):
    session = WorkSession.objects.create(
        user=user,
        unit_id=unit_id,
        clock_in=timestamp,
        current_status='IN'
    )
    live_status.current_state = 'IN'
    live_status.save()
    logger.info("Clock in: User %s at Unit %s", user.id, unit_id)

def _handle_break_or_clock_out(user, unit_id, timestamp, live_status):
    session = WorkSession.objects.filter(
        user=user,
        unit_id=unit_id,
        current_status='IN'
    ).order_by('-clock_in').first()
    
    if not session:
        logger.error("No active session found for user %s at unit %s", user.id, unit_id)
        return
    
    template = ShiftTemplate.objects.filter(
        name__icontains='restaurant'
    ).first()
    
    if template and timestamp.time() >= template.end_time:
        session.clock_out = timestamp
        session.current_status = 'OUT'
        session.save()
        live_status.current_state = 'OUT'
        logger.info("Clock out: User %s at Unit %s", user.id, unit_id)
    else:
        session.current_status = 'BREAK'
        session.save()
        DailyBreakLog.objects.create(
            session=session,
            start_time=timestamp
        )
        live_status.current_state = 'BREAK'
        logger.info("Break start: User %s at Unit %s", user.id, unit_id)

def _handle_break_end(user, unit_id, timestamp, live_status):
    session = WorkSession.objects.filter(
        user=user,
        unit_id=unit_id,
        current_status='BREAK'
    ).order_by('-clock_in').first()
    
    if not session:
        logger.error("No break session found for user %s at unit %s", user.id, unit_id)
        return
    
    break_log = session.breaks.filter(end_time__isnull=True).first()
    if break_log:
        break_log.end_time = timestamp
        break_log.save()
        
        duration = (break_log.end_time - break_log.start_time).total_seconds()
        session.total_break_seconds += int(duration)
        session.current_status = 'IN'
        session.save()
        
        live_status.current_state = 'IN'
        logger.info("Break end: User %s at Unit %s, duration: %s sec", user.id, unit_id, duration)
