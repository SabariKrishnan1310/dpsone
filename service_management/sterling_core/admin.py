from django.contrib import admin
from .models import Organization, Unit, SterlingUser, Membership

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'slug')
    list_filter = ('created_at',)

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit_code', 'organization')
    search_fields = ('name', 'unit_code')
    list_filter = ('organization',)

@admin.register(SterlingUser)
class SterlingUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_global_admin', 'is_superuser', 'is_staff')
    search_fields = ('username', 'email')
    list_filter = ('is_global_admin', 'is_superuser', 'is_staff')

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'unit', 'role', 'is_primary')
    search_fields = ('user__username', 'unit__name')
    list_filter = ('role', 'is_primary', 'unit__organization')
