import uuid
from django.db import models
from sterling_core.models import SterlingUser, Unit

class ShiftTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    grace_period_mins = models.IntegerField(default=15)

    def __str__(self):
        return self.name

class WorkSession(models.Model):
    STATUS_CHOICES = (
        ('IN', 'Clocked In'),
        ('BREAK', 'On Break'),
        ('OUT', 'Clocked Out'),
    )
    user = models.ForeignKey(SterlingUser, on_delete=models.CASCADE, related_name='work_sessions')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='work_sessions')
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

class DailyBreakLog(models.Model):
    session = models.ForeignKey(WorkSession, on_delete=models.CASCADE, related_name='breaks')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Break: {self.session.user.username}"

class UserLiveStatus(models.Model):
    user = models.OneToOneField(SterlingUser, on_delete=models.CASCADE, related_name='live_status')
    current_state = models.CharField(max_length=10, default='OUT')
    last_tap = models.DateTimeField(auto_now=True)
    last_unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['current_state']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.current_state}"
