from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import Teacher, Classroom, Subject, School, TeacherSubjectMapping
from core.services.exceptions import (
    ValidationError, 
    ResourceNotFoundError, 
    BusinessRuleViolation, 
    DuplicateEntryError
)

class TeacherService:
    """
    Handles business logic for teacher management, focusing on subject and classroom assignments.
    """

    @staticmethod
    def _validate_school_context(school_id: int) -> School:
        """Helper to ensure the school context is valid."""
        try:
            return School.objects.get(pk=school_id, is_active=True)
        except School.DoesNotExist:
            raise ResourceNotFoundError(f"School with ID {school_id} not found or is inactive.")

    @staticmethod
    def _validate_teacher(teacher_id: int, school: School) -> Teacher:
        """Helper to check if a teacher exists in the school."""
        try:
            return Teacher.objects.get(pk=teacher_id, school=school)
        except Teacher.DoesNotExist:
            raise ResourceNotFoundError(f"Teacher ID {teacher_id} not found in school {school.pk}.")

    @staticmethod
    def _validate_subject(subject_id: int, school: School) -> Subject:
        """Helper to check if a subject exists in the school."""
        try:
            return Subject.objects.get(pk=subject_id, school=school)
        except Subject.DoesNotExist:
            raise ResourceNotFoundError(f"Subject ID {subject_id} not found in school {school.pk}.")

    @staticmethod
    def _validate_classroom(classroom_id: int, school: School) -> Classroom:
        """Helper to check if a classroom exists in the school."""
        try:
            return Classroom.objects.get(pk=classroom_id, school=school)
        except Classroom.DoesNotExist:
            raise ResourceNotFoundError(f"Classroom ID {classroom_id} not found in school {school.pk}.")

    @classmethod
    @transaction.atomic
    def assign_subject_to_classroom(
        cls, 
        school_id: int,
        teacher_id: int, 
        subject_id: int, 
        classroom_id: int
    ) -> TeacherSubjectMapping:
        """
        Assigns a specific teacher to teach a subject in a classroom, 
        ensuring no conflicting assignments exist.
        """
        # 1. Validation and Resource Retrieval
        school = cls._validate_school_context(school_id)
        teacher = cls._validate_teacher(teacher_id, school)
        subject = cls._validate_subject(subject_id, school)
        classroom = cls._validate_classroom(classroom_id, school)

        # 2. Business Rule: Prevent Duplicate Mapping
        # A specific teacher should not be mapped to the exact same subject and classroom combination twice.
        if TeacherSubjectMapping.objects.filter(
            school=school,
            teacher=teacher,
            subject=subject,
            classroom=classroom
        ).exists():
            raise DuplicateEntryError(
                f"Teacher {teacher.last_name} is already assigned to teach {subject.name} in {classroom.grade}-{classroom.section}."
            )
            
        # 3. Business Rule: Prevent Conflicting Teaching Roles
        # OPTIONAL: Add logic here to prevent a teacher from taking on too many hours 
        # or too many core subjects (e.g., check against a maximum load constraint).
        # This often involves checking the TimetableEntry model (which we haven't implemented a service for yet).

        # 4. Execution (Creation)
        mapping = TeacherSubjectMapping.objects.create(
            school=school,
            teacher=teacher,
            subject=subject,
            classroom=classroom,
            is_active=True
        )

        return mapping

    @classmethod
    @transaction.atomic
    def update_homeroom_assignment(cls, teacher_id: int, classroom_id: int) -> Teacher:
        """
        Assigns or updates a teacher's homeroom responsibility.
        """
        teacher = get_object_or_404(Teacher, pk=teacher_id)
        school = cls._validate_school_context(teacher.school_id)
        
        # 1. Validation: Ensure the classroom is valid
        new_homeroom = cls._validate_classroom(classroom_id, school)
        
        # 2. Business Rule: Prevent multiple homeroom teachers for one class
        if Classroom.objects.filter(homeroom_teacher=teacher).exclude(pk=new_homeroom.pk).exists():
            # Remove the teacher from their old homeroom if applicable
            Classroom.objects.filter(homeroom_teacher=teacher).update(homeroom_teacher=None)

        # 3. Execution
        new_homeroom.homeroom_teacher = teacher
        new_homeroom.save(update_fields=['homeroom_teacher'])

        return teacher