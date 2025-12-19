# core/services/rfid_service.py (FINAL CORRECTED VERSION)

import json
import traceback
from datetime import datetime
from django.contrib.auth import get_user_model 

# --- Import required models from student_management ---
from student_management.models import (
    Student, 
    School, 
    TapLog, 
    AttendanceRecord,
)

# Define the user model using the standard Django method
StudentManagementUser = get_user_model() 


class RfidService:
    @staticmethod
    def process_student_tap(school_id: str, rfid_uid: str, device_id: str, timestamp_str: str):
        """
        Main logic to process an RFID tap, creating a TapLog and AttendanceRecord.
        This method name is specifically process_student_tap to match the call in tasks.py.
        """
        try:
            # 1. Look up School
            try:
                # school_id is passed as a string from the API, convert back to int for FK lookup
                school = School.objects.get(pk=int(school_id))
            except School.DoesNotExist:
                print(f"ERROR: School with ID {school_id} not found.")
                return
            except ValueError:
                # Handles cases where school_id="ABC" instead of "1"
                print(f"ERROR: School ID '{school_id}' is not a valid integer.")
                return

            # 2. Look up Student
            try:
                # Assuming rfid_uid is unique per school
                student = Student.objects.get(school=school, rfid_uid=rfid_uid)
            except Student.DoesNotExist:
                print(f"WARNING: Student not found for RFID UID: {rfid_uid}. Logging tap only.")
                student = None 

            # Prepare timestamp and direction
            # Handles 'Z' for UTC if present
            tap_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Determine direction from device_id convention
            direction = 'IN' if device_id.endswith('_IN') else 'OUT'
            
            # 3. Create TapLog (Raw Log)
            TapLog.objects.create(
                school=school,
                rfid_uid=rfid_uid,
                timestamp=tap_time,
                device_id=device_id,
                direction=direction,
                raw_data={
                    "rfid_uid": rfid_uid, 
                    "device_id": device_id, 
                    "tap_time": timestamp_str, 
                    "school_id": school_id
                }
            )
            print(f"TapLog created successfully for {rfid_uid}")


            # 4. Create Attendance Record (Only if student is found)
            if student:
                # Use get_or_create to prevent duplicate entries for the same date/student
                AttendanceRecord.objects.get_or_create(
                    school=school,
                    student=student,
                    date=tap_time.date(),
                    defaults={
                        'status': 'PRESENT',
                        'tap_timestamp': tap_time,
                        'source': 'RFID'
                    }
                )
                print(f"Attendance record created/updated for {student.last_name}")
            
        except Exception as e:
            # CRITICAL FAILURE: Print the full traceback before letting Celery retry
            print("==========================================================================")
            print(f"CRITICAL DATABASE ERROR processing tap {rfid_uid}: {e}")
            traceback.print_exc() # Prints the detailed error trace
            print("==========================================================================")
            raise # Re-raise to let Celery handle retries