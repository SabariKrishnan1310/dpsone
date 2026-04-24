# core/services/rfid_service.py (FINAL CORRECTED VERSION)

import json
import traceback
import logging
from datetime import datetime, time
from django.contrib.auth import get_user_model 
from django.db import transaction

# --- Import required models from student_management ---
from student_management.models import (
    Student, 
    School, 
    TapLog, 
    AttendanceRecord,
    RFIDCard,
)

# Define the user model using the standard Django method
StudentManagementUser = get_user_model()
logger = logging.getLogger(__name__) 


class RfidService:
    @staticmethod
    @transaction.atomic
    def process_student_tap(school_id: str, rfid_uid: str, device_id: str, timestamp_str: str):
        """
        Implements toggle logic: first tap = IN (PRESENT/LATE), second tap = OUT, etc.
        """
        try:
            # 1. Look up School
            school = School.objects.get(pk=int(school_id))

            # 2. Look up RFIDCard by UID and link to Student
            try:
                rfid_card = RFIDCard.objects.select_related('assigned_to_student').get(
                    school=school, 
                    uid=rfid_uid, 
                    status='ACTIVE'
                )
                student = rfid_card.assigned_to_student
            except RFIDCard.DoesNotExist:
                logger.warning(f"RFID Card with UID {rfid_uid} not found or inactive in school {school.name}.")
                student = None

            # Prepare timestamp
            tap_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            tap_date = tap_time.date()

            # 3. Create TapLog (Raw Log - always created for audit)
            TapLog.objects.create(
                school=school,
                rfid_uid=rfid_uid,
                timestamp=tap_time,
                device_id=device_id,
                direction="NA",  # Not used anymore, but keep for audit
                raw_data={
                    "rfid_uid": rfid_uid, 
                    "device_id": device_id, 
                    "tap_time": timestamp_str, 
                    "school_id": school_id,
                    "student_id": student.pk if student else None
                }
            )

            # 4. Attendance toggle logic
            if student:
                # Get all taps for this student today
                today_taps = TapLog.objects.filter(
                    school=school,
                    rfid_uid=rfid_uid,
                    timestamp__date=tap_date
                ).order_by('timestamp')

                tap_count = today_taps.count()
                # LATE cutoff (e.g., 8:30 AM)
                LATE_CUTOFF_HOUR = 8
                LATE_CUTOFF_MINUTE = 30
                late_cutoff = time(hour=LATE_CUTOFF_HOUR, minute=LATE_CUTOFF_MINUTE)

                # Determine status
                if tap_count == 1:
                    # First tap: IN
                    if tap_time.time() > late_cutoff:
                        status = 'LATE'
                    else:
                        status = 'PRESENT'
                elif tap_count == 2:
                    # Second tap: OUT
                    status = 'OUT'
                else:
                    # Odd tap: IN, Even tap: OUT
                    status = 'PRESENT' if tap_count % 2 == 1 else 'OUT'

                # Create or update AttendanceRecord
                attendance, created = AttendanceRecord.objects.get_or_create(
                    school=school,
                    student=student,
                    date=tap_date,
                    defaults={
                        'status': status,
                        'tap_timestamp': tap_time,
                        'source': 'RFID'
                    }
                )
                if not created:
                    attendance.status = status
                    attendance.tap_timestamp = tap_time
                    attendance.save(update_fields=['status', 'tap_timestamp'])
            else:
                logger.warning(f"Tap {rfid_uid} received but no student assigned - creating TapLog only")

        except Exception as e:
            logger.error(f"CRITICAL DATABASE ERROR processing tap {rfid_uid}: {str(e)}", exc_info=True)
            raise