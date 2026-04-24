from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import Student, Classroom, Parent, School, RFIDCard
from core.services.exceptions import (
    ValidationError, 
    ResourceNotFoundError, 
    BusinessRuleViolation, 
    ObjectNotActiveError,
    DuplicateEntryError
)

class StudentService:
    """Handles business logic related to the Student model, including enrollment and updates."""

    @staticmethod
    def _validate_school_context(school_id: int) -> School:
        """Helper to ensure the school context is valid and active."""
        try:
            school = School.objects.get(pk=school_id)
        except School.DoesNotExist:
            raise ResourceNotFoundError(f"School with ID {school_id} not found.")
        
        if not school.is_active:
            raise ObjectNotActiveError(f"School '{school.name}' is currently inactive.")
        
        return school

    @staticmethod
    def _validate_classroom(classroom_id: int, school: School) -> Classroom:
        """Helper to validate if a classroom exists in the given school and is active."""
        try:
            classroom = Classroom.objects.get(pk=classroom_id, school=school)
        except Classroom.DoesNotExist:
            raise ResourceNotFoundError(f"Classroom ID {classroom_id} not found in school {school.pk}.")
        
        if not classroom.is_active:
            raise ObjectNotActiveError(f"Classroom {classroom.grade}-{classroom.section} is inactive.")
            
        # Optional: Classroom capacity check
        # if classroom.students.count() >= classroom.capacity:
        #     raise BusinessRuleViolation("Classroom has reached maximum capacity.")
            
        return classroom
    
    @staticmethod
    def _validate_unique_enrollment(school: School, admission_number: str):
        """Checks for uniqueness of critical enrollment fields within the school."""
        
        if Student.objects.filter(school=school, admission_number=admission_number).exists():
            raise DuplicateEntryError(f"Admission number '{admission_number}' is already taken.")
            
    @classmethod
    @transaction.atomic
    def enroll_new_student(
        cls, 
        school_id: int, 
        classroom_id: int, 
        parent_id: int, 
        student_data: dict
    ) -> Student:
        """
        Validates all necessary prerequisites and creates a new Student record.
        """
        # 1. Validation and Resource Retrieval
        school = cls._validate_school_context(school_id)
        classroom = cls._validate_classroom(classroom_id, school)
        
        try:
            parent = Parent.objects.get(pk=parent_id, school=school)
        except Parent.DoesNotExist:
            raise ResourceNotFoundError("Parent record must exist before student enrollment.")
        
        # Validate data integrity from input
        required_fields = ['first_name', 'last_name', 'admission_number']
        for field in required_fields:
            if not student_data.get(field):
                raise ValidationError(f"Missing required field: {field}")
                
        # 2. Business Rule Validation (admission_number only, RFID handled separately)
        cls._validate_unique_enrollment(
            school=school, 
            admission_number=student_data.get('admission_number')
        )

        # 3. Execution (Creation)
        student = Student.objects.create(
            school=school,
            classroom=classroom,
            parent=parent,
            first_name=student_data['first_name'],
            last_name=student_data['last_name'],
            dob=student_data.get('dob'),
            admission_number=student_data['admission_number'],
            roll_number=student_data.get('roll_number'),
            gender=student_data.get('gender'),
            is_fully_enrolled=True # Assuming enrollment means they are active
        )
        
        return student

    @classmethod
    @transaction.atomic
    def assign_rfid_card_to_student(cls, student_id: int, rfid_uid: str) -> Student:
        """
        Link an RFID card to a student (separate step from enrollment).
        Can reassign cards between students if needed.
        """
        student = get_object_or_404(Student, pk=student_id)
        school = student.school
        
        # 1. Validate RFID UID is not already assigned to another student in the school
        existing_card = RFIDCard.objects.filter(
            school=school, 
            uid=rfid_uid,
            assigned_to_student__isnull=False
        ).exclude(assigned_to_student=student).first()
        
        if existing_card:
            raise DuplicateEntryError(
                f"RFID UID '{rfid_uid}' is already assigned to {existing_card.assigned_to_student.last_name}."
            )
        
        # 2. Get or create RFIDCard
        rfid_card, created = RFIDCard.objects.get_or_create(
            school=school,
            uid=rfid_uid,
            defaults={
                'assigned_to_student': student,
                'status': 'ACTIVE'
            }
        )
        
        # 3. If card exists but unassigned or assigned to different student, update it
        if not created:
            old_student = rfid_card.assigned_to_student
            if rfid_card.assigned_to_student != student:
                rfid_card.assigned_to_student = student
                rfid_card.status = 'ACTIVE'
                rfid_card.save(update_fields=['assigned_to_student', 'status'])
        
        return student

    @classmethod
    @transaction.atomic
    def unassign_rfid_card_from_student(cls, student_id: int) -> Student:
        """
        Remove RFID card assignment from a student (e.g., lost card, graduated).
        Marks all active RFID cards as lost/inactive.
        """
        student = get_object_or_404(Student, pk=student_id)
        
        # Mark all active RFID cards as lost
        RFIDCard.objects.filter(
            assigned_to_student=student,
            status='ACTIVE'
        ).update(status='LOST')
        
        return student
        
        # 4. Side Effect (Optional: Send welcome email to parent)
        # MessagingService.send_enrollment_confirmation(parent, student)
        
        return student

    @classmethod
    @transaction.atomic
    def update_student_classroom(cls, student_id: int, new_classroom_id: int) -> Student:
        """Transfers a student to a new classroom after validation."""
        
        student = get_object_or_404(Student, pk=student_id)
        
        # 1. Validation: Ensure new classroom is valid within the student's school
        new_classroom = cls._validate_classroom(new_classroom_id, student.school)
        
        # 2. Execution (Update)
        if student.classroom_id != new_classroom_id:
            student.classroom = new_classroom
            student.save(update_fields=['classroom'])
            
            # 3. Side Effect (Optional: Log transfer for audit)
            # LogService.log_event(student.school, 'CLASS_TRANSFER', f'Student {student.pk} transferred to {new_classroom.pk}')
        
        return student