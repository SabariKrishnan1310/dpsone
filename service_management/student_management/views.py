# service_management/student_management/views.py
from rest_framework import generics
from rest_framework.response import Response
from .models import Student
from .serializers import StudentLookupSerializer
from rest_framework.exceptions import NotFound

class StudentLookupView(generics.RetrieveAPIView):
    """
    API endpoint to look up a student's basic details (role, school_id)
    based on their RFID UID. Used by the Ingestion API for data enrichment.
    """
    queryset = Student.objects.all()
    serializer_class = StudentLookupSerializer
    lookup_field = 'rfid_uid'

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            # Ensure the user object is also present (as it's used in the serializer)
            if not instance.user:
                 raise NotFound("Student found, but has no linked user account.")
        except NotFound:
            # Return a simple 404 response if the student isn't found
            raise NotFound("Student not found with this RFID UID.")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
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

        # Filters
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

        # Order by date descending
        return queryset.order_by('-date', 'student__last_name')

# service_management/student_management/views.py

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
# student_management/views.py (add this at the bottom)
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
        
        # Base queryset: today's attendance records
        queryset = AttendanceRecord.objects.filter(date=filter_date)
        
        # Optional classroom filter
        if classroom_id:
            queryset = queryset.filter(student__classroom_id=classroom_id)
        
        # Serialize to simple JSON
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
