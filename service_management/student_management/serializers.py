# service_management/student_management/serializers.py
from rest_framework import serializers
from .models import Student

class StudentLookupSerializer(serializers.ModelSerializer):

    role = serializers.CharField(source='user.role')
    school_id = serializers.IntegerField(source='school.pk')

    class Meta:
        model = Student
        fields = ('rfid_uid', 'school_id', 'role')
from .models import AttendanceRecord, Classroom, Student

class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.last_name', read_only=True)
    classroom = serializers.CharField(source='student.classroom.__str__', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            'id',
            'student_name',
            'student_id',
            'classroom',
            'date',
            'period_number',
            'status',
            'source',
            'verified_by_teacher',
            'tap_timestamp'
        ]
