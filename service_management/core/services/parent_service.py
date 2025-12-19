from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import Parent, Student, School
from core.services.exceptions import (
    ValidationError, 
    BusinessRuleViolation, 
    ResourceNotFoundError,
    DuplicateEntryError
)

class ParentService:
    """
    Handles business logic for Parent records, focusing on creation and the 
    management of parent-student relationships (children).
    """

    @staticmethod
    def _validate_school_context(school_id: int) -> School:
        """Helper to ensure the school context is valid and active."""
        try:
            return School.objects.get(pk=school_id, is_active=True)
        except School.DoesNotExist:
            raise ResourceNotFoundError(f"School with ID {school_id} not found or is inactive.")

    @staticmethod
    def _validate_phone_uniqueness(school: School, phone: str):
        """Checks for uniqueness of the phone number within the school."""
        if Parent.objects.filter(school=school, phone=phone).exists():
            raise DuplicateEntryError(
                f"A parent record with the phone number '{phone}' already exists in this school."
            )

    @classmethod
    @transaction.atomic
    def create_new_parent(cls, school_id: int, parent_data: dict) -> Parent:
        """
        Creates a new parent record after validating uniqueness and school context.
        """
        # 1. Validation and Resource Retrieval
        school = cls._validate_school_context(school_id)
        
        required_fields = ['first_name', 'last_name', 'phone']
        for field in required_fields:
            if not parent_data.get(field):
                raise ValidationError(f"Missing required field: {field} for parent creation.")
        
        phone_number = parent_data['phone']
        cls._validate_phone_uniqueness(school, phone_number)

        # 2. Execution (Creation)
        parent = Parent.objects.create(
            school=school,
            first_name=parent_data['first_name'],
            last_name=parent_data['last_name'],
            phone=phone_number,
            email=parent_data.get('email'),
            is_active=True
        )

        # 3. Side Effect (Optional: Create associated user account/messaging thread)
        # UserService.create_parent_user(parent)
        
        return parent

    @classmethod
    @transaction.atomic
    def link_student_to_parent(cls, student_id: int, parent_id: int) -> Student:
        """
        Links an existing student to an existing parent.
        This is typically used if a student's legal guardian changes.
        """
        
        # 1. Fetch Resources
        student = get_object_or_404(Student, pk=student_id)
        parent = get_object_or_404(Parent, pk=parent_id)
        
        # 2. Validation: Ensure both belong to the same school
        if student.school_id != parent.school_id:
            raise BusinessRuleViolation(
                "Cannot link student and parent from different school contexts."
            )
        
        # 3. Execution (Update)
        student.parent = parent
        student.save(update_fields=['parent'])
        
        # 4. Side Effect (Audit log)
        # LogService.log_event(student.school, 'PARENT_LINKAGE_UPDATE', f'Student {student.pk} assigned to new parent {parent.pk}')
        
        return student

    @classmethod
    @transaction.atomic
    def unlink_student_from_parent(cls, student_id: int) -> Student:
        """
        Removes the parent linkage from a student (e.g., in a data migration 
        or before deletion). This usually requires assigning a 'dummy' or 
        'system' parent if the field is not null.
        """
        student = get_object_or_404(Student, pk=student_id)
        
        # Business Rule: Parent linkage is MANDATORY (based on typical Django model ForeignKey constraint)
        # You would typically raise an error unless the parent is being replaced.
        # Assuming the parent field is not nullable (PROTECT):
        
        raise BusinessRuleViolation(
            "Student must always have a primary parent. Use 'link_student_to_parent' to reassign."
        )
        
        # If the parent field was nullable, the code would be:
        # student.parent = None
        # student.save(update_fields=['parent'])
        # return student