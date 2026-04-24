from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import (
    School, StudentManagementUser, Announcement, MessageThread, Message, Student, Teacher
)
from core.services.exceptions import (
    ValidationError, 
    BusinessRuleViolation, 
    ResourceNotFoundError
)

class MessagingService:
    """
    Handles business logic for all communications: announcements and private messages,
    ensuring targeted delivery and adherence to roles.
    """

    @staticmethod
    def _validate_user(user_id: int, school: School) -> StudentManagementUser:
        """Helper to ensure the user exists and belongs to the school."""
        try:
            user = StudentManagementUser.objects.get(pk=user_id, school=school)
        except StudentManagementUser.DoesNotExist:
            raise ResourceNotFoundError(f"User ID {user_id} not found in school {school.pk}.")
        if not user.is_active:
            raise BusinessRuleViolation(f"User ID {user_id} is inactive.")
        return user
    
    @staticmethod
    def _validate_school_context(school_id: int) -> School:
        """Helper to ensure the school context is valid and active."""
        try:
            return School.objects.get(pk=school_id, is_active=True)
        except School.DoesNotExist:
            raise ResourceNotFoundError(f"School with ID {school_id} not found or is inactive.")

    

    @classmethod
    @transaction.atomic
    def publish_announcement(
        cls, 
        school_id: int, 
        author_id: int, 
        title: str, 
        content: str, 
        target_roles: list[str]
    ) -> Announcement:
        """
        Creates and publishes a school-wide announcement targeting specific user roles.
        """
        school = cls._validate_school_context(school_id)
        author = cls._validate_user(author_id, school)
        
        
        
        if author.role not in ['Admin', 'Principal', 'Staff']:
            raise BusinessRuleViolation("Only authorized users can publish school announcements.")

        
        valid_roles = [role[0] for role in StudentManagementUser.ROLE_CHOICES]
        if not all(role in valid_roles for role in target_roles):
             raise ValidationError("One or more target roles are invalid.")

        
        announcement = Announcement.objects.create(
            school=school,
            author=author,
            title=title,
            content=content,
            
            target_roles=target_roles, 
            is_published=True,
            published_at=datetime.now()
        )
        
        
        
        
        return announcement

    

    @classmethod
    @transaction.atomic
    def start_new_thread(
        cls, 
        school_id: int, 
        sender_id: int, 
        recipient_ids: list[int], 
        subject: str
    ) -> MessageThread:
        """
        Creates a new message thread involving one sender and multiple recipients.
        """
        school = cls._validate_school_context(school_id)
        
        
        sender = cls._validate_user(sender_id, school)
        recipients = [cls._validate_user(rid, school) for rid in recipient_ids]
        
        
        if sender_id in recipient_ids:
            raise BusinessRuleViolation("Cannot start a thread with yourself listed as a recipient.")

        
        all_participants = [sender] + recipients
        
        thread = MessageThread.objects.create(
            school=school,
            subject=subject
        )
        
        
        thread.participants.set(all_participants) 

        return thread

    @classmethod
    @transaction.atomic
    def send_message(
        cls, 
        thread_id: int, 
        sender_id: int, 
        content: str
    ) -> Message:
        """
        Adds a message to an existing thread.
        """
        thread = get_object_or_404(MessageThread, pk=thread_id)
        school = thread.school
        
        
        sender = cls._validate_user(sender_id, school)
        if sender not in thread.participants.all():
            raise BusinessRuleViolation("Sender is not a participant in this message thread.")

        
        message = Message.objects.create(
            thread=thread,
            sender=sender,
            content=content,
            sent_at=datetime.now()
        )
        
        
        thread.last_message_at = message.sent_at
        thread.save(update_fields=['last_message_at'])
        
        

        return message
