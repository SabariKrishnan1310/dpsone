
from django.contrib import admin
from django import forms 
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    StudentManagementUser, 
    School, 
    Classroom, 
    Teacher, 
    Parent, 
    Student,
    TapLog, 
    AttendanceRecord,
    RFIDCard,
    Subject,
    TeacherSubjectMapping, 
    TimetableEntry,
    Announcement,
    MessageThread,
    Message,
    CanteenItem,
    Wallet,
    WalletTransaction,
)


class StudentManagementUserChangeForm(forms.ModelForm):
    class Meta:
        model = StudentManagementUser
        fields = '__all__'
        
class StudentManagementUserCreationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = StudentManagementUser
        fields = ('email', 'first_name', 'last_name', 'role', 'school')

    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords don't match.")
        return password2
        

class CustomUserAdmin(BaseUserAdmin):
    """Admin configuration for the custom user model."""
    
    form = StudentManagementUserChangeForm
    add_form = StudentManagementUserCreationForm

    list_display = ('email', 'first_name', 'last_name', 'role', 'school', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}), 
        ('Personal info', {'fields': ('first_name', 'last_name', 'role', 'school')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'password2'), 
        }),
        ('Personal info', {'fields': ('first_name', 'last_name', 'role', 'school')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}), 
    )

class StudentInline(admin.StackedInline):
    model = Student
    can_delete = False
    verbose_name_plural = 'Student Profile'
    
class TeacherInline(admin.StackedInline):
    model = Teacher
    can_delete = False
    verbose_name_plural = 'Teacher Profile'

class ParentInline(admin.StackedInline):
    model = Parent
    can_delete = False
    verbose_name_plural = 'Parent Profile'
    
class StudentManagementUserAdmin(CustomUserAdmin):
    """Main registration for the User model with inlines"""
    inlines = [StudentInline, TeacherInline, ParentInline] 

admin.site.register(StudentManagementUser, StudentManagementUserAdmin)



@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('school', 'grade', 'section', 'class_teacher', 'room_number')
    list_filter = ('school', 'grade')
    search_fields = ('grade', 'section')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'subject_specialization', 'is_active')
    search_fields = ('last_name', 'first_name')
    list_filter = ('school', 'subject_specialization')
    
@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'relation')
    search_fields = ('last_name', 'first_name')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('roll_number', 'last_name', 'first_name', 'classroom', 'get_rfid_status', 'is_active')
    list_filter = ('school', 'classroom', 'is_active')
    search_fields = ('last_name', 'admission_number')
    readonly_fields = ('get_active_rfid_card',)
    
    fieldsets = (
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'dob', 'gender', 'blood_group', 'photo_url')
        }),
        ('Enrollment', {
            'fields': ('school', 'classroom', 'parent', 'admission_number', 'roll_number', 'is_active')
        }),
        ('RFID Info (Read-Only)', {
            'fields': ('get_active_rfid_card',),
            'description': 'RFID cards are linked via the RFIDCard model. Use the RFIDCard admin below to assign cards.'
        }),
    )
    
    def get_rfid_status(self, obj):
        """Display RFID assignment status"""
        rfid_card = obj.rfid_cards.filter(status='ACTIVE').first()
        if rfid_card:
            return f"✅ {rfid_card.uid}"
        return "❌ No Active Card"
    get_rfid_status.short_description = 'RFID Card Status'
    
    def get_active_rfid_card(self, obj):
        """Display active RFID card details"""
        rfid_card = obj.rfid_cards.filter(status='ACTIVE').first()
        if rfid_card:
            return f"UID: {rfid_card.uid} | Status: {rfid_card.status} | Issued: {rfid_card.issued_at}"
        return "No active RFID card assigned"
    get_active_rfid_card.short_description = 'Active RFID Card'



@admin.register(TapLog)
class TapLogAdmin(admin.ModelAdmin):
    list_display = ('rfid_uid', 'timestamp', 'direction', 'device_id', 'school')
    list_filter = ('school', 'direction')
    search_fields = ('rfid_uid', 'device_id')
    readonly_fields = ('timestamp', 'raw_data')

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status', 'tap_timestamp', 'source')
    list_filter = ('school', 'status', 'date')
    search_fields = ('student__last_name',)
    date_hierarchy = 'date'

@admin.register(RFIDCard)
class RFIDCardAdmin(admin.ModelAdmin):
    list_display = ('uid', 'status', 'assigned_to_student', 'assigned_to_teacher', 'issued_at')
    list_filter = ('school', 'status', 'issued_at')
    search_fields = ('uid', 'assigned_to_student__last_name', 'assigned_to_teacher__last_name')
    
    fieldsets = (
        ('Card Information', {
            'fields': ('school', 'uid', 'status')
        }),
        ('Assignments', {
            'fields': ('assigned_to_student', 'assigned_to_teacher'),
            'description': 'A card can be assigned to either a student OR a teacher, not both.'
        }),
        ('Timestamps', {
            'fields': ('issued_at',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Validation: Ensure card is only assigned to one person"""
        if obj.assigned_to_student and obj.assigned_to_teacher:
            from django.core.exceptions import ValidationError as DjangoValidationError
            raise DjangoValidationError("A card cannot be assigned to both student and teacher.")
        super().save_model(request, obj, form, change)
    

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'school')
    list_filter = ('school',)

@admin.register(TeacherSubjectMapping)
class TeacherSubjectMappingAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'classroom', 'is_active')
    list_filter = ('school', 'is_active')

@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ('classroom', 'day_of_week', 'period_number', 'subject', 'teacher')
    list_filter = ('school', 'day_of_week', 'classroom')
    list_editable = ('teacher',)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'scope', 'classroom', 'created_by')
    list_filter = ('scope', 'school')

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('student', 'balance', 'updated_at')
    search_fields = ('student__last_name',)
    list_filter = ('school',)

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'type', 'amount', 'timestamp')
    list_filter = ('type', 'school')

@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher', 'created_at')
    list_filter = ('school',)
