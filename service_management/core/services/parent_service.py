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
        school = cls._validate_school_context(school_id)
        
        required_fields = ['first_name', 'last_name', 'phone']
        for field in required_fields:
            if not parent_data.get(field):
                raise ValidationError(f"Missing required field: {field} for parent creation.")
        
        phone_number = parent_data['phone']
        cls._validate_phone_uniqueness(school, phone_number)

        parent = Parent.objects.create(
            school=school,
            first_name=parent_data['first_name'],
            last_name=parent_data['last_name'],
            phone=phone_number,
            email=parent_data.get('email'),
            is_active=True
        )

        
        return parent

    @classmethod
    @transaction.atomic
    def link_student_to_parent(cls, student_id: int, parent_id: int) -> Student:
        """
        Links an existing student to an existing parent.
        This is typically used if a student's legal guardian changes.
        """
        
        student = get_object_or_404(Student, pk=student_id)
        parent = get_object_or_404(Parent, pk=parent_id)
        
        if student.school_id != parent.school_id:
            raise BusinessRuleViolation(
                "Cannot link student and parent from different school contexts."
            )
        
        student.parent = parent
        student.save(update_fields=['parent'])
        
        
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
        
        
        raise BusinessRuleViolation(
            "Student must always have a primary parent. Use 'link_student_to_parent' to reassign."
        )
        
