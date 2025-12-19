# service_management/student_management/models.py (FINAL CORRECTED VERSION)

from django.db import models
# Import necessary classes for custom user
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager 
from django.utils import timezone 
from django.utils.translation import gettext_lazy as _ 

# --- Utility Choices ---
GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
RELATION_CHOICES = [('MOTHER', 'Mother'), ('FATHER', 'Father'), ('GUARDIAN', 'Guardian')]
CARD_STATUS_CHOICES = [('ACTIVE', 'Active'), ('LOST', 'Lost'), ('DAMAGED', 'Damaged')]
ATTENDANCE_STATUS_CHOICES = [('PRESENT', 'Present'), ('ABSENT', 'Absent'), ('OUT', 'Out of School'), ('LATE', 'Late Arrival')]
TAP_DIRECTION_CHOICES = [('IN', 'In'), ('OUT', 'Out')]
TAP_SOURCE_CHOICES = [('RFID', 'RFID Tap'), ('MANUAL', 'Manual Entry')]
TRANSACTION_TYPE_CHOICES = [('CREDIT', 'Credit (Deposit)'), ('DEBIT', 'Debit (Purchase/Fee)')]
DEVICE_STATUS_CHOICES = [('ONLINE', 'Online'), ('OFFLINE', 'Offline'), ('ERROR', 'Error')]
DEVICE_TYPE_CHOICES = [('GATE', 'Main Gate Reader'), ('LIBRARY', 'Library Scanner'), ('CANTEEN', 'Canteen POS'), ('BUS', 'Bus Scanner')]
ERROR_SEVERITY_CHOICES = [('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')]
# ---

# =========================================================================
# 1. CORE TENANCY MODEL
# =========================================================================

class School(models.Model):
    """The top-level organizational unit for multi-tenancy."""
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "School Tenant"
        verbose_name_plural = "School Tenants"

    def __str__(self):
        return self.name

# =========================================================================
# 2. AUTH / CUSTOM USER MODEL 
# =========================================================================

class StudentManagementUserManager(BaseUserManager):
    """Custom user model manager where email is the unique identifier."""
    # Note: The school parameter is optional for create_superuser for bootstrapping.
    def create_user(self, email, password, school=None, role='Student', **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        if not school:
            # Handle case where school is not provided (e.g., during superuser creation)
            try:
                school = School.objects.get(slug='default-school')
            except School.DoesNotExist:
                raise ValueError(_('Users must be associated with a school and the default school does not exist.'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, school=school, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db) # Use save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        # REMOVE role from extra_fields and control it explicitly
        extra_fields.pop('role', None)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        school, created = School.objects.get_or_create(
            slug='default-school',
            defaults={'name': 'Default School', 'is_active': True}
        )

        return self.create_user(
            email=email,
            password=password,
            school=school,
            role='Admin',
            **extra_fields
        )


class StudentManagementUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model supporting different roles (Student, Teacher, Parent, Admin).
    """
    ROLE_CHOICES = [
        ('Student', 'Student'),
        ('Teacher', 'Teacher'),
        ('Parent', 'Parent'),
        ('Admin', 'Admin'),
        ('Staff', 'Staff'),
    ]

    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    # Role is now directly on the user model
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Student') 
    
    # All users must belong to a school
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name='users') 

    objects = StudentManagementUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'school']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"


# =========================================================================
# 3. SCHOOL STRUCTURE MODELS (Linking profiles to the custom user)
# =========================================================================

class Teacher(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teachers') 
    # Link to custom user model 
    user = models.OneToOneField(
        StudentManagementUser, on_delete=models.CASCADE, related_name='teacher_profile', 
        null=True, blank=True, limit_choices_to={'role': 'Teacher'}
    )
    
    first_name = models.CharField(max_length=100) 
    last_name = models.CharField(max_length=100)  
    subject_specialization = models.CharField(max_length=100)
    photo_url = models.URLField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['last_name']

    def __str__(self):
        return f"Teacher: {self.last_name}"

class Classroom(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classrooms') 
    
    grade = models.IntegerField()
    section = models.CharField(max_length=10)
    class_teacher = models.ForeignKey(
        'Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='homeroom_class'
    )
    room_number = models.CharField(max_length=10)

    class Meta:
        unique_together = ('school', 'grade', 'section')
        ordering = ['grade', 'section']

    def __str__(self):
        return f"Grade {self.grade} - {self.section}"

class Parent(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='parents')
    # Link to custom user model 
    user = models.OneToOneField(
        StudentManagementUser, on_delete=models.CASCADE, related_name='parent_profile', 
        null=True, blank=True, limit_choices_to={'role': 'Parent'}
    )

    first_name = models.CharField(max_length=100) 
    last_name = models.CharField(max_length=100)  
    relation = models.CharField(max_length=20, choices=RELATION_CHOICES)
    
    class Meta:
        ordering = ['last_name']

    def __str__(self):
        return f"Parent: {self.last_name}"

class Student(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='students')
    # Link to custom user model
    user = models.OneToOneField(
        StudentManagementUser, on_delete=models.PROTECT, related_name='student_profile', 
        null=True, blank=True, limit_choices_to={'role': 'Student'}
    )
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    dob = models.DateField()
    roll_number = models.IntegerField() 
    is_fully_enrolled = models.BooleanField(default=False)
    
    classroom = models.ForeignKey(Classroom, on_delete=models.PROTECT, related_name='students')
    # Parent FK is to the Parent Profile model
    parent = models.ForeignKey(Parent, on_delete=models.PROTECT, related_name='children')
    
    photo_url = models.URLField(max_length=200, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=5, blank=True)
    
    rfid_uid = models.CharField(max_length=50, db_index=True) 
    admission_number = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = [('school', 'admission_number'), ('school', 'rfid_uid')]
        ordering = ['roll_number']

    def __str__(self):
        return f"R.No {self.roll_number} - {self.last_name}"

# Missing model required by TeacherService
class TeacherSubjectMapping(models.Model):
    """Maps a Teacher to a Subject in a specific Classroom."""
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teacher_subject_mappings')
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE) 
    classroom = models.ForeignKey('Classroom', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('teacher', 'subject', 'classroom')
        verbose_name = "Teacher Subject Mapping"
        verbose_name_plural = "Teacher Subject Mappings"

# =========================================================================
# 4. RFID SYSTEM MODELS
# ... (all other models remain the same)
# =========================================================================

class RFIDCard(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='rfid_cards')
    
    uid = models.CharField(max_length=20, db_index=True)
    
    assigned_to_student = models.ForeignKey(
        Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='rfid_card'
    )
    assigned_to_teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='rfid_card'
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=CARD_STATUS_CHOICES, default='ACTIVE')
    
    class Meta:
        unique_together = ('school', 'uid')
        ordering = ['uid']

    def __str__(self):
        return f"Card {self.uid} ({self.status})"

class TapLog(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='tap_logs') 
    
    rfid_uid = models.CharField(max_length=50, db_index=True)
    timestamp = models.DateTimeField()
    device_id = models.CharField(max_length=100)
    direction = models.CharField(max_length=5, choices=TAP_DIRECTION_CHOICES)
    raw_data = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Raw Tap Log"
        verbose_name_plural = "Raw Tap Logs"
        ordering = ['-timestamp']

# =========================================================================
# 5. TIMETABLE MODELS
# =========================================================================

class Subject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='subjects') 
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    
    class Meta:
        verbose_name = "Academic Subject"
        verbose_name_plural = "Academic Subjects"
        unique_together = ('school', 'name', 'code')
        ordering = ['name']

    def __str__(self):
        return self.name

class TimetableEntry(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='timetable_entries') 
    
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='timetable_entries')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='timetable_entries')
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name='timetable_entries')
    
    day_of_week = models.IntegerField(choices=[(i, f'Day {i}') for i in range(7)])
    period_number = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        verbose_name = "Timetable Entry"
        verbose_name_plural = "Timetable Entries"
        unique_together = ('classroom', 'day_of_week', 'period_number')
        ordering = ['classroom', 'day_of_week', 'period_number']

    def __str__(self):
        return f"{self.classroom.grade}-{self.classroom.section} | {self.subject.code} | Day {self.day_of_week}"

# =========================================================================
# 6. ATTENDANCE MODELS
# =========================================================================

class AttendanceRecord(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='attendance_records') 
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(db_index=True)
    period_number = models.IntegerField(null=True, blank=True)
    
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS_CHOICES)
    
    tap_timestamp = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=10, choices=TAP_SOURCE_CHOICES, default='MANUAL')
    verified_by_teacher = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Attendance Record"
        unique_together = ('student', 'date', 'period_number')
        ordering = ['-date', 'student__last_name']

class PracticeOutRecord(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='practice_out_records') 
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='practice_out_records')
    requested_by_teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name='requested_out_records')
    approved_by_class_teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name='approved_out_records', 
                                                  limit_choices_to={'is_active': True}) 
    date = models.DateField()
    start_period = models.IntegerField()
    end_period = models.IntegerField()
    reason = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Practice Out Record"
        verbose_name_plural = "Practice Out Records"
        ordering = ['-date']

# =========================================================================
# 7. HOMEWORK MODELS
# =========================================================================

class Homework(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='homework_assignments') 
    
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, related_name='assigned_homework')
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='homework_assignments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='homework_assignments')
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField()
    attachment_url = models.URLField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Homework Assignment"
        verbose_name_plural = "Homework Assignments"
        ordering = ['-due_date']

class HomeworkSubmission(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='homework_submissions') 
    
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='homework_submissions')
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    file_url = models.URLField(max_length=500, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Homework Submission"
        verbose_name_plural = "Homework Submissions"
        unique_together = ('homework', 'student')

# =========================================================================
# 8. COMMUNICATION MODELS
# =========================================================================

class Announcement(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='announcements') 
    
    SCOPE_CHOICES = [('SCHOOL', 'School-wide'), ('CLASS', 'Specific Class'), ('TEACHER', 'Teacher Announcement')]
    
    title = models.CharField(max_length=255)
    body = models.TextField()
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default='SCHOOL')
    
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements')
    # Link to Teacher model
    created_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, related_name='posted_announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    attachment_url = models.URLField(max_length=500, null=True, blank=True)
    
    class Meta:
        verbose_name = "School Announcement"
        verbose_name_plural = "School Announcements"
        ordering = ['-created_at']

class MessageThread(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='message_threads') 
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='communication_threads')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='communication_threads')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Message Thread"
        verbose_name_plural = "Message Threads"
        unique_together = ('student', 'teacher')
        ordering = ['-created_at']

class Message(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='messages') 
    
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name='messages')
    # Use CharField for sender_id based on original intent, though User ForeignKey is recommended.
    sender_id = models.CharField(max_length=50) 
    
    message_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    attachment_url = models.URLField(max_length=500, null=True, blank=True)

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['timestamp']

# =========================================================================
# 9. CANTEEN/FINANCIAL MODELS
# =========================================================================

class CanteenItem(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='canteen_items') 
    
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Canteen Item"
        verbose_name_plural = "Canteen Items"
        unique_together = ('school', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (${self.price})"

class Wallet(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='wallets') 
    
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Wallet"
        verbose_name_plural = "Student Wallets"

    def __str__(self):
        return f"Wallet for {self.student.last_name}: ${self.balance}"

class WalletTransaction(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='wallet_transactions') 
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    type = models.CharField(max_length=6, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    item = models.ForeignKey(CanteenItem, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True) 

    class Meta:
        verbose_name = "Wallet Transaction"
        verbose_name_plural = "Wallet Transactions"
        ordering = ['-timestamp']

# =========================================================================
# 10. LIBRARY SYSTEM MODELS
# =========================================================================

class Book(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='library_books') 
    
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, null=True, blank=True)
    category = models.CharField(max_length=100)
    rack = models.CharField(max_length=20) 
    copies_total = models.PositiveIntegerField(default=1)
    copies_available = models.PositiveIntegerField(default=1) 

    class Meta:
        verbose_name = "Library Book"
        verbose_name_plural = "Library Books"
        unique_together = ('school', 'isbn')
        ordering = ['title']

    def __str__(self):
        return self.title

class BookIssue(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='book_issues') 
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='issued_books')
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name='issue_records')
    
    issued_at = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    returned_at = models.DateField(null=True, blank=True)
    
    fine_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Book Issue Record"
        verbose_name_plural = "Book Issue Records"
        ordering = ['-issued_at']

# =========================================================================
# 11. EVENT & COMPETITION MODELS
# =========================================================================

class Event(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='events') 
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()
    category = models.CharField(max_length=100)
    class_limit = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True)
    attachment_url = models.URLField(max_length=500, null=True, blank=True)
    
    class Meta:
        verbose_name = "School Event"
        verbose_name_plural = "School Events"
        ordering = ['date']

    def __str__(self):
        return self.name

class EventRegistration(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='event_registrations') 
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='event_registrations')
    
    REGISTER_STATUS_CHOICES = [('ACCEPTED', 'Accepted'), ('REJECTED', 'Rejected'), ('WAITLIST', 'Waitlist')]
    registered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=REGISTER_STATUS_CHOICES, default='ACCEPTED')

    class Meta:
        verbose_name = "Event Registration"
        verbose_name_plural = "Event Registrations"
        unique_together = ('event', 'student')
        ordering = ['registered_at']

class Certificate(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='certificates') 
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='certificates')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='certificates_awarded')
    
    certificate_url = models.URLField(max_length=500) 
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Award Certificate"
        verbose_name_plural = "Award Certificates"
        unique_together = ('event', 'student')

# =========================================================================
# 12. EXAMS & MARKS MODELS
# =========================================================================

class Exam(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='exams') 
    
    name = models.CharField(max_length=100)
    term = models.CharField(max_length=50)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='exams')
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        verbose_name = "Academic Exam"
        verbose_name_plural = "Academic Exams"
        unique_together = ('school', 'name', 'classroom')
        ordering = ['start_date']

class ExamSubject(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='exam_subjects') 
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='exam_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='exam_subjects')
    
    max_marks = models.PositiveIntegerField()
    exam_date = models.DateField()

    class Meta:
        verbose_name = "Exam Subject Detail"
        verbose_name_plural = "Exam Subject Details"
        unique_together = ('exam', 'subject')

class MarkEntry(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='mark_entries') 
    
    exam_subject = models.ForeignKey(ExamSubject, on_delete=models.CASCADE, related_name='mark_entries')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='marks_records')
    
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Mark Entry"
        verbose_name_plural = "Mark Entries"
        unique_together = ('exam_subject', 'student')

# =========================================================================
# 13. DEVICE MANAGEMENT & ANALYTICS
# =========================================================================

class CollectorNode(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='collector_nodes') 
    
    floor_number = models.IntegerField(null=True, blank=True)
    mac_address = models.CharField(max_length=17, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=DEVICE_STATUS_CHOICES, default='OFFLINE')
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Collector Node"
        verbose_name_plural = "Collector Nodes"
        unique_together = ('school', 'mac_address')

class ReaderDevice(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='reader_devices') 
    
    node = models.ForeignKey(CollectorNode, on_delete=models.CASCADE, related_name='reader_devices')
    
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPE_CHOICES)
    location_description = models.CharField(max_length=255)
    
    status = models.CharField(max_length=10, default='OK')
    last_seen = models.DateTimeField(null=True, blank=True)
    firmware_version = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = "Reader Device"
        verbose_name_plural = "Reader Devices"
        ordering = ['node', 'location_description']

class DeviceErrorLog(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='device_error_logs') 
    
    device = models.ForeignKey('ReaderDevice', on_delete=models.SET_NULL, null=True, blank=True, related_name='error_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField()
    
    severity = models.CharField(max_length=10, choices=ERROR_SEVERITY_CHOICES)

    class Meta:
        verbose_name = "Device Error Log"
        verbose_name_plural = "Device Error Logs"
        ordering = ['-timestamp']

class AttendanceStatsDaily(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='attendance_stats_daily') 
    
    date = models.DateField()
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='daily_stats')
    
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)
    out_count = models.PositiveIntegerField(default=0)
    late_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Daily Attendance Statistic"
        verbose_name_plural = "Daily Attendance Statistics"
        unique_together = ('school', 'date', 'classroom')
        ordering = ['-date']