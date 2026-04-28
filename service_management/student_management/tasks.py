import json
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Student, AttendanceRecord
from core.services.rfid_service import RfidService
from core.services.exceptions import BaseServiceException

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_tap_from_queue(self, tap_data_json: str):
    """
    Process student tap, update DB, and broadcast live via WebSocket.
    """
    rfid_uid = "UNKNOWN"
    try:
        tap_data = json.loads(tap_data_json)
        rfid_uid = tap_data.get('uid')
        device_id = tap_data.get('device')
        timestamp_str = tap_data.get('tap_time')
        school_id = tap_data.get('school')

        if not all([rfid_uid, device_id, timestamp_str, school_id]):
            print(f"ERROR: Missing essential keys in task data. Data: {tap_data}")
            return

        RfidService.process_student_tap(
            rfid_uid=rfid_uid,
            device_id=device_id,
            timestamp_str=timestamp_str,
            school_id=school_id
        )

        try:
            student = Student.objects.select_related('classroom').get(rfid_uid=rfid_uid)
            attendance_record = AttendanceRecord.objects.filter(student=student).latest('tap_timestamp')
        except Student.DoesNotExist:
            print(f"Student with UID {rfid_uid} not found for live broadcast.")
            return
        except AttendanceRecord.DoesNotExist:
            print(f"No attendance record found for student {rfid_uid} to broadcast.")
            return

        channel_layer = get_channel_layer()
        group_name = f"school_{school_id}"

        event_data = {
            "timestamp": attendance_record.tap_timestamp.isoformat() if attendance_record.tap_timestamp else None,
            "student_name": f"{student.first_name} {student.last_name}",
            "grade": student.classroom.grade,
            "section": student.classroom.section,
            "status": attendance_record.status,
            "device_id": device_id
        }

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "tap_event",  # matches consumer
                "message": event_data
            }
        )

    except BaseServiceException as e:
        print(f"SERVICE ERROR for {rfid_uid}: {e.message}. Skipping retry.")

    except Exception as exc:
        print(f"CRITICAL ERROR processing {rfid_uid}: {exc}. Retrying...")
        raise self.retry(exc=exc)
