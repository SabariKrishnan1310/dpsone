from django.contrib import admin
from .models import ShiftTemplate, WorkSession, DailyBreakLog, UserLiveStatus

@admin.register(ShiftTemplate)
class ShiftTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time', 'grace_period_mins')
    list_filter = ('name',)

@admin.register(WorkSession)
class WorkSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'unit', 'date', 'clock_in', 'clock_out', 'current_status', 'net_work_minutes')
    list_filter = ('current_status', 'unit', 'date')
    search_fields = ('user__username', 'unit__name')
    readonly_fields = ('net_work_minutes',)

@admin.register(DailyBreakLog)
class DailyBreakLogAdmin(admin.ModelAdmin):
    list_display = ('session', 'start_time', 'end_time')
    list_filter = ('session__unit',)

@admin.register(UserLiveStatus)
class UserLiveStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_state', 'last_tap', 'last_unit')
    list_filter = ('current_state',)
    search_fields = ('user__username',)
