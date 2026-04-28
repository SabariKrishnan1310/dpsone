from datetime import datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import (
    Event, EventRegistration, School, Student, Teacher
)
from core.services.exceptions import (
    ValidationError, 
    BusinessRuleViolation, 
    ResourceNotFoundError,
    DuplicateEntryError
)

class EventsService:
    """
    Handles business logic for managing school events, including creation, 
    registration, and capacity enforcement.
    """

    @staticmethod
    def _validate_school_context(school_id: int) -> School:
        """Helper to ensure the school context is valid and active."""
        try:
            return School.objects.get(pk=school_id, is_active=True)
        except School.DoesNotExist:
            raise ResourceNotFoundError(f"School with ID {school_id} not found or is inactive.")

    @classmethod
    @transaction.atomic
    def create_event(
        cls, 
        school_id: int, 
        title: str, 
        description: str, 
        start_time_str: str, 
        end_time_str: str, 
        max_capacity: int = 0
    ) -> Event:
        """
        Creates a new school event with defined time and capacity limits.
        """
        school = cls._validate_school_context(school_id)

        
        try:
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
        except ValueError:
            raise ValidationError("Start and end times must be in ISO 8601 format.")
        
        if start_time >= end_time:
            raise BusinessRuleViolation("Event start time must be before the end time.")
            
        if start_time < datetime.now():
            raise BusinessRuleViolation("Cannot create an event in the past.")

        if max_capacity < 0:
            raise ValidationError("Max capacity cannot be negative.")

        
        event = Event.objects.create(
            school=school,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            max_capacity=max_capacity,
            current_registrations=0 
        )

        return event

    

    @classmethod
    @transaction.atomic
    def register_for_event(cls, event_id: int, user_id: int, user_role: str) -> EventRegistration:
        """
        Registers a student or teacher for an event, enforcing capacity limits.
        """
        event = get_object_or_404(Event, pk=event_id)
        
        
        if event.end_time < datetime.now():
            raise BusinessRuleViolation("Event registration is closed as the event has ended.")
        
        if not event.is_active:
            raise BusinessRuleViolation("Event is currently inactive and cannot accept registrations.")

        
        if event.max_capacity > 0 and event.current_registrations >= event.max_capacity:
            raise BusinessRuleViolation(
                f"Event Registration Limit Violated: '{event.title}' is full (Max Capacity: {event.max_capacity})."
            )

        
        if user_role == 'Student':
            try:
                user_instance = Student.objects.get(pk=user_id, school=event.school)
            except Student.DoesNotExist:
                raise ResourceNotFoundError(f"Student ID {user_id} not found.")
        elif user_role == 'Teacher':
            try:
                user_instance = Teacher.objects.get(pk=user_id, school=event.school)
            except Teacher.DoesNotExist:
                raise ResourceNotFoundError(f"Teacher ID {user_id} not found.")
        else:
            raise ValidationError("Invalid role specified for registration.")

        
        if EventRegistration.objects.filter(event=event, user_role=user_role, user_id=user_id).exists():
            raise DuplicateEntryError("This user is already registered for this event.")

        
        registration = EventRegistration.objects.create(
            event=event,
            user_role=user_role,
            user_id=user_id, 
            registered_at=datetime.now()
        )
        
        
        event.current_registrations = EventRegistration.objects.filter(event=event).count()
        event.save(update_fields=['current_registrations'])
        
        
        

        return registration

    @classmethod
    @transaction.atomic
    def cancel_registration(cls, registration_id: int) -> Event:
        """
        Cancels a user's registration and updates the event capacity counter.
        """
        registration = get_object_or_404(EventRegistration, pk=registration_id)
        event = registration.event
        
        
        registration.delete()
        
        
        event.current_registrations = EventRegistration.objects.filter(event=event).count()
        event.save(update_fields=['current_registrations'])
        
        return event
