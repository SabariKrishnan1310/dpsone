from rest_framework import serializers
from .models import Student, RFIDCard, AttendanceRecord

class RFIDCardSerializer(serializers.ModelSerializer):
    """Serializer for RFID Card information"""
    class Meta:
        model = RFIDCard
        fields = ('uid', 'status', 'issued_at')


class StudentLookupSerializer(serializers.ModelSerializer):
    """Serializer for student lookup via RFID UID"""
    role = serializers.CharField(source='user.role', read_only=True)
    school_id = serializers.IntegerField(source='school.pk', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    active_rfid_card = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = (
            'id',
            'first_name',
            'last_name',
            'roll_number',
            'admission_number',
            'school_id',
            'school_name',
            'role',
            'active_rfid_card'
        )
    
    def get_active_rfid_card(self, obj):
        """Return active RFID card details"""
        rfid_card = obj.rfid_cards.filter(status='ACTIVE').first()
        if rfid_card:
            return RFIDCardSerializer(rfid_card).data
        return None
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
