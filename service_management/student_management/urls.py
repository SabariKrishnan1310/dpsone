from django.urls import path
from .views import StudentLookupView, attendance_records, LiveAttendanceAnalyticsView

urlpatterns = [
    path('lookup/<str:rfid_uid>/', StudentLookupView.as_view(), name='student-lookup'),
    path('attendance/', attendance_records, name='attendance-records'),  # <-- new endpoint
    path('live-attendance/', LiveAttendanceAnalyticsView.as_view(), name='live-attendance'),
]
