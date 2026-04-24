from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import (
    TimetableEntry, Teacher, Classroom, Subject, School, StudentManagementUser
)
from core.services.exceptions import (
    ValidationError, 
    BusinessRuleViolation, 
    ResourceNotFoundError,
    DuplicateEntryError
)

class TimetableService:
    """
    Handles business logic for creating and managing Timetable Entries, 
    enforcing constraints against double-booking teachers, classrooms, and time slots.
    """

    @staticmethod
    def _validate_school_context(school_id: int) -> School:
        """Helper to ensure the school context is valid and active."""
        try:
            return School.objects.get(pk=school_id, is_active=True)
        except School.DoesNotExist:
            raise ResourceNotFoundError(f"School with ID {school_id} not found or is inactive.")

    @staticmethod
    def _get_resource_by_id(model, pk: int, school: School, resource_name: str):
        """Generic helper to fetch a resource."""
        try:
            return model.objects.get(pk=pk, school=school)
        except model.DoesNotExist:
            raise ResourceNotFoundError(f"{resource_name} ID {pk} not found in school {school.pk}.")

    @classmethod
    def _check_time_conflict(cls, school: School, day_of_week: str, start_time: str, end_time: str, exclude_id: int = None):
        """
        Checks for any existing timetable entries that overlap with the proposed slot.
        """
        
        try:
            datetime.strptime(start_time, "%H:%M:%S")
            datetime.strptime(end_time, "%H:%M:%S")
        except ValueError:
            raise ValidationError("Time must be provided in 'HH:MM:SS' format.")
        
        
        conflict_query = TimetableEntry.objects.filter(
            school=school,
            day_of_week=day_of_week,
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if exclude_id:
            conflict_query = conflict_query.exclude(pk=exclude_id)
            
        return conflict_query


    @classmethod
    @transaction.atomic
    def create_timetable_entry(
        cls,
        school_id: int,
        day_of_week: str,
        start_time: str,
        end_time: str,
        teacher_id: int,
        classroom_id: int,
        subject_id: int,
    ) -> TimetableEntry:
        """
        Creates a new timetable entry after checking for time conflicts across all resources.
        """
        school = cls._validate_school_context(school_id)
        teacher = cls._get_resource_by_id(Teacher, teacher_id, school, 'Teacher')
        classroom = cls._get_resource_by_id(Classroom, classroom_id, school, 'Classroom')
        subject = cls._get_resource_by_id(Subject, subject_id, school, 'Subject')
        
        
        teacher_conflicts = cls._check_time_conflict(school, day_of_week, start_time, end_time).filter(teacher=teacher)
        if teacher_conflicts.exists():
            raise BusinessRuleViolation(
                f"Teacher {teacher.last_name} is already booked for an overlapping slot."
            )

        classroom_conflicts = cls._check_time_conflict(school, day_of_week, start_time, end_time).filter(classroom=classroom)
        if classroom_conflicts.exists():
            raise BusinessRuleViolation(
                f"Classroom {classroom.room_number} is already booked for an overlapping slot."
            )

        entry = TimetableEntry.objects.create(
            school=school,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            teacher=teacher,
            classroom=classroom,
            subject=subject,
        )

        return entry
    
    @classmethod
    @transaction.atomic
    def update_timetable_entry(cls, entry_id: int, update_data: dict) -> TimetableEntry:
        """
        Updates an existing timetable entry, re-validating conflicts based on new data.
        """
        entry = get_object_or_404(TimetableEntry, pk=entry_id)
        school = entry.school
        
        day_of_week = update_data.get('day_of_week', entry.day_of_week)
        start_time = update_data.get('start_time', entry.start_time.isoformat())
        end_time = update_data.get('end_time', entry.end_time.isoformat())
        teacher = entry.teacher # Default to existing teacher
        classroom = entry.classroom # Default to existing classroom
        
        if 'teacher_id' in update_data:
            teacher = cls._get_resource_by_id(Teacher, update_data['teacher_id'], school, 'Teacher')
            entry.teacher = teacher
        if 'classroom_id' in update_data:
            classroom = cls._get_resource_by_id(Classroom, update_data['classroom_id'], school, 'Classroom')
            entry.classroom = classroom
        if 'subject_id' in update_data:
            entry.subject = cls._get_resource_by_id(Subject, update_data['subject_id'], school, 'Subject')

        
        teacher_conflicts = cls._check_time_conflict(school, day_of_week, start_time, end_time, exclude_id=entry_id).filter(teacher=teacher)
        if teacher_conflicts.exists():
            raise BusinessRuleViolation(
                f"Update failed: Teacher {teacher.last_name} is already booked for an overlapping slot."
            )

        classroom_conflicts = cls._check_time_conflict(school, day_of_week, start_time, end_time, exclude_id=entry_id).filter(classroom=classroom)
        if classroom_conflicts.exists():
            raise BusinessRuleViolation(
                f"Update failed: Classroom {classroom.room_number} is already booked for an overlapping slot."
            )

        entry.day_of_week = day_of_week
        entry.start_time = start_time
        entry.end_time = end_time
        
        entry.save()
        
        return entry
