from datetime import date, timedelta
import datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import Student, Book, BookIssue, School
from core.services.exceptions import (
    ValidationError, 
    BusinessRuleViolation, 
    ResourceNotFoundError,
    ObjectNotActiveError
)

class LibraryService:
    """
    Handles business logic and constraints for book issuance and returns, 
    including stock management and borrowing limits.
    """

    MAX_BOOKS_PER_STUDENT = 1
    DEFAULT_ISSUE_PERIOD_DAYS = 7
    FINE_PER_DAY = 0.50  

    @staticmethod
    def _validate_school_context(school_id: int) -> School:
        """Helper to ensure the school context is valid and active."""
        try:
            return School.objects.get(pk=school_id, is_active=True)
        except School.DoesNotExist:
            raise ResourceNotFoundError(f"School with ID {school_id} not found or is inactive.")

    @staticmethod
    def _validate_student_can_borrow(student: Student):
        """Checks if a student is eligible to borrow a book based on rules."""
        
        
        if not student.is_fully_enrolled:
            raise ObjectNotActiveError("Student is not fully enrolled/is inactive and cannot borrow books.")

        
        overdue_issues = BookIssue.objects.filter(
            student=student, 
            returned_at__isnull=True, 
            due_date__lt=date.today()
        ).count()
        if overdue_issues > 0:
            raise BusinessRuleViolation(
                f"Student has {overdue_issues} book(s) overdue. Please return them before borrowing more."
            )

        
        current_issues = BookIssue.objects.filter(
            student=student, 
            returned_at__isnull=True
        ).count()
        if current_issues >= LibraryService.MAX_BOOKS_PER_STUDENT:
            raise BusinessRuleViolation(
                f"Student has reached the maximum borrowing limit ({LibraryService.MAX_BOOKS_PER_STUDENT} books)."
            )

    @classmethod
    @transaction.atomic
    def issue_book(cls, student_id: int, book_id: int, issuer_user=None) -> BookIssue:
        """
        Issues a book to a student after validating all borrowing rules and updating stock.
        """
        
        try:
            student = Student.objects.select_related('school').get(pk=student_id)
        except Student.DoesNotExist:
            raise ResourceNotFoundError(f"Student ID {student_id} not found.")

        
        cls._validate_school_context(student.school_id)
        
        try:
            book = Book.objects.get(pk=book_id, school=student.school)
        except Book.DoesNotExist:
            raise ResourceNotFoundError(f"Book ID {book_id} not found in school {student.school.name}.")

        
        cls._validate_student_can_borrow(student)

        
        if book.current_stock <= 0:
            raise BusinessRuleViolation(f"Book '{book.title}' is currently out of stock.")
            
        
        if BookIssue.objects.filter(student=student, book=book, returned_at__isnull=True).exists():
            raise BusinessRuleViolation("This book is already checked out by this student.")

        
        book.current_stock -= 1
        book.save(update_fields=['current_stock'])

        due_date = date.today() + timedelta(days=cls.DEFAULT_ISSUE_PERIOD_DAYS)

        book_issue = BookIssue.objects.create(
            student=student,
            book=book,
            school=student.school,
            issued_by=issuer_user, 
            due_date=due_date
        )

        return book_issue
    
    @classmethod
    @transaction.atomic
    def return_book(cls, book_issue_id: int, receiver_user=None) -> tuple[BookIssue, float]:
        """
        Processes a book return, calculates fines, and updates stock.
        Returns the updated BookIssue and the calculated fine amount.
        """
        book_issue = get_object_or_404(
            BookIssue, 
            pk=book_issue_id, 
            returned_at__isnull=True
        )
        
        
        fine_amount = 0.0
        is_overdue = book_issue.due_date < date.today()
        
        if is_overdue:
            overdue_days = (date.today() - book_issue.due_date).days
            fine_amount = overdue_days * cls.FINE_PER_DAY
        
        
        book_issue.returned_at = datetime.now()
        book_issue.received_by = receiver_user
        book_issue.fine_amount = fine_amount
        book_issue.save(update_fields=['returned_at', 'received_by', 'fine_amount'])
        
        
        book = book_issue.book
        book.current_stock += 1
        book.save(update_fields=['current_stock'])

        
        
        
        
        

        return book_issue, fine_amount
