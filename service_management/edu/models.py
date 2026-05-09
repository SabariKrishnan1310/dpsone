import uuid
from django.db import models
from sterling_core.models import SterlingUser, Unit

class Grade(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='grades', null=True, blank=True)
    name = models.CharField(max_length=50) # e.g. Nursery, Grade 1, Grade 10

    def __str__(self):
        return f"{self.unit.name if self.unit else 'Global'} - {self.name}"

class Section(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='sections', null=True, blank=True)
    name = models.CharField(max_length=10) # e.g. A, B, C
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='sections')

    def __str__(self):
        return f"{self.grade.name} {self.name} ({self.unit.name if self.unit else 'Global'})"

class Classroom(models.Model):
    name = models.CharField(max_length=50) # e.g. Room 101, Science Lab 2
    section = models.OneToOneField(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='classroom')

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=100) # e.g. Mathematics, English

    def __str__(self):
        return self.name

class EduProfile(models.Model):
    ROLE_CHOICES = (
        ('STUDENT', 'Student'),
        ('TEACHER', 'Teacher'),
        ('STAFF', 'Staff'),
        ('ADMIN', 'Admin'),
    )
    user = models.OneToOneField(SterlingUser, on_delete=models.CASCADE, related_name='edu_profile')
    role_type = models.CharField(max_length=10, choices=ROLE_CHOICES)
    
    # Student Specifics
    home_section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    roll_number = models.CharField(max_length=20, blank=True)
    
    # Teacher Specifics
    class_teacher_for = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='class_teacher')
    subjects = models.ManyToManyField(Subject, blank=True, related_name='teachers')
    
    # Staff Specifics
    department = models.CharField(max_length=100, blank=True)
    shift_start = models.TimeField(null=True, blank=True)
    shift_end = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_type_display()}"

class TimetableSlot(models.Model):
    DAYS = (
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
        ('SUN', 'Sunday'),
    )
    teacher = models.ForeignKey(SterlingUser, on_delete=models.CASCADE, related_name='teaching_slots')
    subject = models.CharField(max_length=100)
    classroom = models.CharField(max_length=100)
    day_of_week = models.CharField(max_length=3, choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.subject} - {self.classroom} ({self.day_of_week})"

class AttendanceRecord(models.Model):
    STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('LATE', 'Late'),
        ('ABSENT', 'Absent'),
        ('IN_SHIFT', 'In Shift'),
        ('ON_BREAK', 'On Break'),
    )
    user = models.ForeignKey(SterlingUser, on_delete=models.CASCADE, related_name='attendance_records')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(auto_now_add=True)
    first_tap = models.DateTimeField(null=True, blank=True)
    last_tap = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PRESENT')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.status}"

class StaffWorkSession(models.Model):
    STATUS_CHOICES = (
        ('IN', 'Clocked In'),
        ('BREAK', 'On Break'),
        ('OUT', 'Clocked Out'),
    )
    user = models.ForeignKey(SterlingUser, on_delete=models.CASCADE, related_name='staff_sessions')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='staff_sessions')
    date = models.DateField(auto_now_add=True)
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(null=True, blank=True)
    total_break_seconds = models.BigIntegerField(default=0)
    current_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='IN')

    @property
    def net_work_minutes(self):
        from django.utils import timezone
        end = self.clock_out or timezone.now()
        total_seconds = (end - self.clock_in).total_seconds()
        return int((total_seconds - self.total_break_seconds) / 60)

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class LiveSchoolStatus(models.Model):
    user = models.OneToOneField(SterlingUser, on_delete=models.CASCADE, related_name='live_school_status')
    current_location = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=20, default='OUT')
    last_tap = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['state']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.state}"

class SchoolConfig(models.Model):
    THEME_CHOICES = (
        ('LIGHT', 'Light'),
        ('DARK', 'Dark'),
    )
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name='school_config')
    late_threshold = models.TimeField(default='08:15')
    grace_period = models.IntegerField(default=15)
    theme_mode = models.CharField(max_length=10, choices=THEME_CHOICES, default='LIGHT')
    auto_notify_parents = models.BooleanField(default=False)

    def __str__(self):
        return f"Config for {self.unit.name}"
