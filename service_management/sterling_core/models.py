import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Unit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='units')
    name = models.CharField(max_length=255)
    unit_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f'{self.organization.name} - {self.name}'

class SterlingUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=False, null=True, blank=True)
    hashed_rfid = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    is_global_admin = models.BooleanField(default=False)
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username

    @property
    def accessible_units(self):
        return self.memberships.all().select_related('unit')

    @property
    def is_owner(self):
        return self.memberships.filter(role='OWNER').exists()

class Membership(models.Model):
    ROLE_CHOICES = (
        ('OWNER', 'Owner'),
        ('MANAGER', 'Manager'),
        ('SUPERVISOR', 'Supervisor'),
        ('STAFF', 'Staff'),
        ('MEMBER', 'Member'),
    )
    user = models.ForeignKey(SterlingUser, related_name='memberships', on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, related_name='memberships', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_primary = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'unit')
        indexes = [models.Index(fields=['user', 'role'])]

    def __str__(self):
        return f'{self.user.username} @ {self.unit.name} ({self.role})'
