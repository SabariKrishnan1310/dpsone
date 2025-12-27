from uuid import uuid4

def attendance_event_payload(attendance):
    return {
        "type": "attendance.event",
        "event_id": str(uuid4()),
        "timestamp": attendance.timestamp.isoformat(),

        "student": {
            "id": attendance.student.id,
            "name": attendance.student.full_name,
            "grade": attendance.student.grade,
            "section": attendance.student.section,
        },

        "attendance": {
            "status": attendance.status,
            "method": "NFC",
            "device_id": attendance.device_id,
        },

        "school": {
            "id": attendance.school_id,
        }
    }
