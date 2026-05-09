from django.contrib import admin
from .models import EduProfile, TimetableSlot, AttendanceRecord, StaffWorkSession, LiveSchoolStatus, SchoolConfig, Grade, Section, Classroom, Subject

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade')
    list_filter = ('grade',)

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'section')

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(EduProfile)
class EduProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role_type', 'home_section', 'roll_number')
    list_filter = ('role_type', 'home_section')
    search_fields = ('user__username', 'roll_number')

@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'classroom', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('day_of_week', 'teacher')
    search_fields = ('subject', 'classroom', 'teacher__username')

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'unit', 'date', 'first_tap', 'last_tap', 'status')
    list_filter = ('status', 'date', 'unit')
    search_fields = ('user__username',)
    readonly_fields = ('metadata',)

@admin.register(StaffWorkSession)
class StaffWorkSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'unit', 'date', 'clock_in', 'clock_out', 'current_status', 'net_work_minutes')
    list_filter = ('current_status', 'unit', 'date')
    search_fields = ('user__username', 'unit__name')
    readonly_fields = ('net_work_minutes',)

@admin.register(LiveSchoolStatus)
class LiveSchoolStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_location', 'state', 'last_tap')
    list_filter = ('state',)
    search_fields = ('user__username',)
