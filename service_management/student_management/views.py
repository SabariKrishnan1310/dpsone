from rest_framework import generics
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from .models import Student, RFIDCard, AttendanceRecord
from .serializers import StudentLookupSerializer, AttendanceRecordSerializer

class StudentLookupView(generics.RetrieveAPIView):
    """
    API endpoint to look up a student's basic details (role, school_id)
    based on their RFID UID. Used by the Ingestion API for data enrichment.
    Now looks up via RFIDCard relationship instead of Student.rfid_uid.
    """
    serializer_class = StudentLookupSerializer
    
    def get_object(self):
        rfid_uid = self.kwargs.get('rfid_uid')
        
        try:
            rfid_card = RFIDCard.objects.select_related(
                'assigned_to_student',
                'assigned_to_student__school'
            ).get(
                uid=rfid_uid,
                status='ACTIVE'
            )
            
            student = rfid_card.assigned_to_student
            
            if not student:
                raise NotFound(detail="RFID card exists but not assigned to any student.")
            
            return student
            
        except RFIDCard.DoesNotExist:
            raise NotFound(detail=f"No active RFID card found with UID: {rfid_uid}")
from rest_framework import generics
from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer

class AttendanceRecordsView(generics.ListAPIView):
    """
    API endpoint to fetch attendance records.
    Supports filtering by classroom_id, grade, section, date range.
    """
    serializer_class = AttendanceRecordSerializer

    def get_queryset(self):
        queryset = AttendanceRecord.objects.select_related('student', 'student__classroom').all()

        classroom_id = self.request.query_params.get('classroom_id')
        grade = self.request.query_params.get('grade')
        section = self.request.query_params.get('section')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if classroom_id:
            queryset = queryset.filter(student__classroom_id=classroom_id)
        if grade:
            queryset = queryset.filter(student__classroom__grade=grade)
        if section:
            queryset = queryset.filter(student__classroom__section=section)
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return queryset.order_by('-date', 'student__last_name')


from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Student, AttendanceRecord  # assuming AttendanceRecord exists
from django.utils.dateparse import parse_datetime

@api_view(['GET'])
def attendance_records(request):
    """
    Returns JSON list of attendance records.
    Optional query params:
      - grade: int
      - section: str
    """
    records = AttendanceRecord.objects.select_related('student').all()
    
    grade = request.GET.get('grade')
    section = request.GET.get('section')
    
    if grade:
        records = records.filter(student__grade=grade)
    if section:
        records = records.filter(student__section__iexact=section)
    
    data = []
    for r in records.order_by('-timestamp')[:100]:  # latest 100 records
        data.append({
            "timestamp": r.timestamp.isoformat(),
            "student_name": r.student.full_name,  # assuming Student model has full_name
            "grade": r.student.grade,
            "section": r.student.section,
            "status": r.status  # e.g., 'Present' or 'Absent'
        })
    
    return Response(data)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import AttendanceRecord, Classroom, Student

class LiveAttendanceAnalyticsView(APIView):
    """
    Returns recent attendance taps, optionally filtered by classroom.
    Query params:
      - classroom_id (int, optional)
      - date (YYYY-MM-DD, optional, default today)
    """
    def get(self, request):
        date_str = request.GET.get("date")
        classroom_id = request.GET.get("classroom_id")
        
        if date_str:
            try:
                filter_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            filter_date = timezone.now().date()
        
        queryset = AttendanceRecord.objects.filter(date=filter_date)
        
        if classroom_id:
            queryset = queryset.filter(student__classroom_id=classroom_id)
        
        data = [
            {
                "student_name": f"{record.student.first_name} {record.student.last_name}",
                "rfid_uid": record.student.rfid_uid,
                "timestamp": record.tap_timestamp,
                "device": getattr(record, "device_id", None),
                "status": record.status,
                "classroom": f"{record.student.classroom.grade}-{record.student.classroom.section}"
            }
            for record in queryset.order_by("-tap_timestamp")[:100]  # limit to last 100 taps
        ]
        
        return Response({"records": data})
