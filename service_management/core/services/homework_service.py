from datetime import date, datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
from student_management.models import (
    Homework, HomeworkSubmission, Teacher, Classroom, Subject, Student, School
)
from core.services.exceptions import (
    ValidationError, 
    BusinessRuleViolation, 
    ResourceNotFoundError
)

class HomeworkService:
    """
    Handles business logic for homework management: creation, assignment, 
    submission, and grading.
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
        """Generic helper to fetch a resource by ID and school."""
        try:
            return model.objects.get(pk=pk, school=school)
        except model.DoesNotExist:
            raise ResourceNotFoundError(f"{resource_name} ID {pk} not found in school {school.pk}.")

    

    @classmethod
    @transaction.atomic
    def create_assignment(
        cls, 
        school_id: int,
        teacher_id: int, 
        subject_id: int, 
        classroom_ids: list[int],
        title: str,
        description: str,
        due_date_str: str,
        max_marks: float = 10.0
    ) -> Homework:
        """
        Creates a new homework assignment and links it to one or more classrooms.
        """
        school = cls._validate_school_context(school_id)
        teacher = cls._get_resource_by_id(Teacher, teacher_id, school, 'Teacher')
        subject = cls._get_resource_by_id(Subject, subject_id, school, 'Subject')
        
        
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Due date must be in 'YYYY-MM-DD' format.")
        
        if due_date <= date.today():
            raise BusinessRuleViolation("Due date must be a future date.")
        
        if max_marks <= 0:
            raise ValidationError("Maximum marks must be positive.")

        
        classrooms = []
        for cid in classroom_ids:
            
            classrooms.append(cls._get_resource_by_id(Classroom, cid, school, 'Classroom'))

        
        homework = Homework.objects.create(
            school=school,
            teacher=teacher,
            subject=subject,
            title=title,
            description=description,
            due_date=due_date,
            max_marks=max_marks
        )
        
        
        homework.classrooms.set(classrooms)
        
        
        
        
        return homework

    

    @classmethod
    @transaction.atomic
    def submit_homework(cls, homework_id: int, student_id: int, submission_data: dict) -> HomeworkSubmission:
        """
        Records a student's submission for a specific homework assignment.
        """
        homework = get_object_or_404(Homework, pk=homework_id)
        
        try:
            student = Student.objects.get(pk=student_id, school=homework.school)
        except Student.DoesNotExist:
            raise ResourceNotFoundError(f"Student ID {student_id} not found in school {homework.school.name}.")

        
        if student.classroom not in homework.classrooms.all():
            raise BusinessRuleViolation(
                f"Student {student.admission_number} is not assigned this homework."
            )
            
        
        if date.today() > homework.due_date:
            submission_data['is_late'] = True
        else:
            submission_data['is_late'] = False
        
        
        if HomeworkSubmission.objects.filter(homework=homework, student=student).exists():
            
            
            raise BusinessRuleViolation("Student has already submitted this homework.")

        
        submission = HomeworkSubmission.objects.create(
            homework=homework,
            student=student,
            submission_text=submission_data.get('submission_text'),
            submission_file_url=submission_data.get('submission_file_url'),
            submitted_at=datetime.now(),
            is_late=submission_data['is_late']
        )
        
        return submission

    

    @classmethod
    @transaction.atomic
    def grade_submission(cls, submission_id: int, grader_id: int, marks_obtained: float, feedback: str = None) -> HomeworkSubmission:
        """
        Records the marks and feedback for a student's homework submission.
        """
        submission = get_object_or_404(HomeworkSubmission, pk=submission_id)
        homework = submission.homework
        school = homework.school
        
        
        grader = cls._get_resource_by_id(StudentManagementUser, grader_id, school, 'User')
        
        
        if grader.teacher != homework.teacher and not grader.is_admin:
            raise BusinessRuleViolation("Grader is not authorized to mark this submission.")

        
        if marks_obtained < 0 or marks_obtained > homework.max_marks:
            raise ValidationError(
                f"Marks obtained ({marks_obtained}) must be between 0 and the max marks ({homework.max_marks})."
            )

        
        submission.marks_obtained = marks_obtained
        submission.feedback = feedback
        submission.graded_at = datetime.now()
        submission.is_graded = True
        submission.save(update_fields=['marks_obtained', 'feedback', 'graded_at', 'is_graded'])
        
        
        

        return submission
