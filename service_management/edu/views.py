import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView, ListView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.db.models import Count, Q
import hashlib
import json

from .models import EduProfile, SchoolConfig, SterlingUser, AttendanceRecord, LiveSchoolStatus, TimetableSlot
from sterling_core.models import Unit

logger = logging.getLogger(__name__)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def edu_login(request):
    """Custom login with Redis session caching and role-based routing."""
    if request.user.is_authenticated:
        # Multi-Role Routing: sabari -> /nexus/, principal_ben -> /edu/dashboard/
        if request.user.is_superuser:
            return redirect('nexus:dashboard')
        elif request.user.memberships.filter(role='MANAGER').exists():
            return redirect('edu:dashboard')
        elif hasattr(request.user, 'edu_profile'):
            return redirect('edu:dashboard')
        else:
            return redirect('edu:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            # Cache user session in Redis
            cache.set(f"user_session_{user.id}", {
                'user_id': str(user.id),
                'username': user.username,
                'is_staff': user.is_staff,
            }, timeout=3600)
            
            # Role-based redirect
            if user.is_superuser:
                return redirect('nexus:dashboard')
            elif user.memberships.filter(role='MANAGER').exists():
                return redirect('edu:dashboard')
            else:
                return redirect('edu:dashboard')
        else:
            messages.error(request, "Invalid username or password")
    
    return render(request, 'edu/login.html')

def edu_logout(request):
    """Custom logout with cache cleanup."""
    if request.user.is_authenticated:
        cache.delete(f"user_session_{request.user.id}")
        logout(request)
    return redirect('edu:login')

@login_required
def dashboard(request):
    """Dashboard with Redis caching and context for Identity Modal."""
    cache_key = f"dashboard_html_{request.user.id}"
    cached_html = cache.get(cache_key)
    # Temporary disable html cache for dev/testing
    # if cached_html:
    #     return cached_html
    
    # Get units for the identity creation modal
    units = cache.get('units_list')
    if not units:
        units = list(Unit.objects.values('id', 'name'))
        cache.set('units_list', units, 300)
    
    # Get sections for the identity modal dropdowns
    from .models import Section, Grade
    sections = cache.get('sections_list')
    if not sections:
        sections = list(Section.objects.select_related('grade').values('id', 'name', 'grade__name')[:50])
        cache.set('sections_list', sections, 300)
    
    roles = EduProfile.ROLE_CHOICES
    
    response = render(request, 'edu/dashboard.html', {
        'units': units,
        'roles': roles,
        'sections': sections
    })
    # cache.set(cache_key, response, 60)  # Cache for 1 minute
    return response

@login_required
def dashboard_data(request):
    """API endpoint - optimized with Redis and ORM tricks."""
    from django.utils import timezone
    
    today = timezone.now().date()
    cache_key = f"dashboard_data_{today}"
    
    # Try Redis cache first
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)
    
    # Optimized queries with select_related and prefetch_related
    teachers = EduProfile.objects.filter(role_type='TEACHER')
    teachers_on_duty = LiveSchoolStatus.objects.filter(
        Q(state='IN') | Q(state='ON_BREAK'),
        state__isnull=False
    ).select_related('user').count()
    
    students = EduProfile.objects.filter(role_type='STUDENT')
    students_present = AttendanceRecord.objects.filter(
        date=today,
        status__in=['PRESENT', 'LATE']
    ).select_related('user', 'unit').count()
    
    late_count = AttendanceRecord.objects.filter(
        date=today,
        status='LATE'
    ).count()
    
    # Recent taps - optimized with only() to reduce data transfer
    recent_taps = []
    records = AttendanceRecord.objects.filter(
        date=today
    ).select_related('user', 'unit', 'user__edu_profile').order_by('-last_tap')[:20]
    
    for record in records:
        profile = getattr(record.user, 'edu_profile', None)
        recent_taps.append({
            'name': record.user.username,
            'role': profile.get_role_type_display() if profile else 'Unknown',
            'status': record.get_status_display(),
            'time': record.last_tap.strftime('%H:%M:%S') if record.last_tap else '',
            'location': record.unit.name if record.unit else ''
        })
    
    data = {
        'teachers_on_duty': teachers_on_duty,
        'teachers_total': teachers.count(),
        'students_present': students_present,
        'students_total': students.count(),
        'late_count': late_count,
        'ingestion_rate': '0.0',  # TODO: calculate from Redis
        'recent_taps': recent_taps
    }
    
    # Cache in Redis for 30 seconds
    cache.set(cache_key, data, 30)
    
    return JsonResponse(data)

class IdentityCreateView(CreateView):
    """Create user with RFID hashing - optimized."""
    model = SterlingUser
    template_name = 'edu/identity_form.html'
    success_url = reverse_lazy('edu:dashboard')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop('instance', None)  # Remove instance since we're using a standard Form, not ModelForm
        return kwargs
    
    def get_form_class(self):
        from django import forms
        class IdentityForm(forms.Form):
            first_name = forms.CharField(required=False)
            last_name = forms.CharField(required=False)
            role = forms.CharField(required=False)
            rfid_number = forms.CharField(required=False)
        return IdentityForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Cache units in Redis
        cache_key = 'units_list'
        units = cache.get(cache_key)
        if not units:
            units = list(Unit.objects.values('id', 'name'))
            cache.set(cache_key, units, 300)
        context['units'] = units
        return context
    
    def form_valid(self, form):
        raw_rfid = self.request.POST.get('rfid_number')
        first_name = self.request.POST.get('first_name', '')
        last_name = self.request.POST.get('last_name', '')
        role = self.request.POST.get('role', 'student').upper()
        
        # Tenant scope: only allow creating identity for user's unit
        user = self.request.user
        membership = user.memberships.filter(is_primary=True).first()
        if not membership and not user.is_superuser:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("No primary unit assigned")
        
        assigned_unit_id = membership.unit.id if membership else None
        
        # Generate a username if needed
        username = f"{first_name.lower()}.{last_name.lower()}".replace(" ", "")
        if not username:
            username = f"user_{hashlib.md5(str(raw_rfid).encode()).hexdigest()[:8]}"
            
        if raw_rfid:
            hashed = hashlib.sha256(raw_rfid.encode()).hexdigest()
            
            if SterlingUser.objects.filter(username=username).exists():
                user = SterlingUser.objects.get(username=username)
                user.hashed_rfid = hashed
                user.first_name = first_name
                user.last_name = last_name
                user.save()
            else:
                user = SterlingUser(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    hashed_rfid=hashed
                )
                user.set_unusable_password()
                user.save()
            
            # Role-based EduProfile fields
            from .models import EduProfile, Section, Subject
            
            profile_kwargs = {
                'role_type': role,
            }
            
            if role == 'STUDENT':
                section_id = self.request.POST.get('home_section')
                roll_no = self.request.POST.get('roll_number')
                if section_id:
                    profile_kwargs['home_section_id'] = section_id
                profile_kwargs['roll_number'] = roll_no or ''
                
            elif role == 'TEACHER':
                section_id = self.request.POST.get('class_teacher_for')
                department = self.request.POST.get('department')
                if section_id:
                    profile_kwargs['class_teacher_for_id'] = section_id
                profile_kwargs['department'] = department or ''
            
            elif role == 'STAFF':
                profile_kwargs['department'] = self.request.POST.get('department') or ''
                profile_kwargs['shift_start'] = self.request.POST.get('shift_start') or None
                profile_kwargs['shift_end'] = self.request.POST.get('shift_end') or None
            
            EduProfile.objects.update_or_create(user=user, defaults=profile_kwargs)
            
            # Warm Redis cache - CRITICAL for hardware
            from sterling_core.signals import get_redis_client
            try:
                r = get_redis_client()
                r.hset(f"cache:rfid:{hashed}", mapping={
                    "user_id": str(user.id),
                    "name": f"{first_name} {last_name}".strip(),
                    "role": role.capitalize(),
                    "primary_unit_id": str(assigned_unit_id) if assigned_unit_id else ""
                })
            except Exception as e:
                logger.error(f"Failed to warm RFID cache: {e}")
            
            messages.success(self.request, f"User {user.username} created with RFID hashed. Hardware ready!")
        
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return redirect('edu:dashboard')

@login_required
def settings_view(request):
    """Settings with caching."""
    from .models import SchoolConfig
    
    if request.method == 'POST':
        unit_id = request.POST.get('unit')
        late_threshold = request.POST.get('late_threshold')
        grace_period = request.POST.get('grace_period')
        theme_mode = request.POST.get('theme_mode')
        auto_notify = request.POST.get('auto_notify_parents') == 'on'
        
        unit = Unit.objects.get(id=unit_id) if unit_id else None
        
        config, created = SchoolConfig.objects.get_or_create(
            unit=unit,
            defaults={
                'late_threshold': late_threshold,
                'grace_period': grace_period,
                'theme_mode': theme_mode,
                'auto_notify_parents': auto_notify
            }
        )
        
        if not created:
            config.late_threshold = late_threshold
            config.grace_period = grace_period
            config.theme_mode = theme_mode
            config.auto_notify_parents = auto_notify
            config.save()
        
        # Clear cache
        cache.delete('school_configs')
        messages.success(request, "Settings updated successfully.")
        return redirect('edu:settings')
    
    # Cache configs
    configs = cache.get('school_configs')
    if not configs:
        configs = list(SchoolConfig.objects.select_related('unit').values(
            'id', 'unit__name', 'late_threshold', 'grace_period', 'theme_mode'
        ))
        cache.set('school_configs', configs, 300)
    
    units = cache.get('units_list')
    if not units:
        units = list(Unit.objects.values('id', 'name'))
        cache.set('units_list', units, 300)
    
    return render(request, 'edu/settings.html', {
        'configs': configs,
        'units': units
    })

class StaffListView(ListView):
    """Staff management - optimized."""
    model = EduProfile
    template_name = 'edu/staff.html'
    context_object_name = 'staff_list'
    
    def get_queryset(self):
        return EduProfile.objects.filter(
            role_type__in=['TEACHER', 'ADMIN']
        ).select_related('user').prefetch_related('user__memberships')

class StudentListView(ListView):
    """Student directory - optimized."""
    model = EduProfile
    template_name = 'edu/students.html'
    context_object_name = 'students_list'
    
    def get_queryset(self):
        return EduProfile.objects.filter(
            role_type='STUDENT'
        ).select_related('user')

from sterling_core.mixins import TenantScopeMixin

@login_required
def student_hub(request):
    # Manual scoping since these are functions, not CBVs
    user = request.user
    if not user.is_superuser:
        membership = user.memberships.filter(is_primary=True).first()
        if not membership:
            return HttpResponseForbidden("No primary unit assigned")
        unit = membership.unit
    else:
        unit = None

    from .models import EduProfile, Grade, Section
    students = EduProfile.objects.filter(role_type='STUDENT').select_related('user', 'home_section', 'home_section__grade')
    if unit:
        students = students.filter(home_section__unit=unit) # Assuming Section has Unit FK
    
    grades = Grade.objects.all()
    sections = Section.objects.all()
    if unit:
        sections = sections.filter(grade__unit=unit) # This depends on model structure
    
    return render(request, 'edu/student_hub.html', {'students': students, 'grades': grades, 'sections': sections})

@login_required
def teacher_hub(request):
    from .models import EduProfile
    teachers = EduProfile.objects.filter(role_type='TEACHER').select_related('user', 'class_teacher_for').prefetch_related('subjects')
    return render(request, 'edu/teacher_hub.html', {'teachers': teachers})

from django.http import HttpResponseForbidden

@login_required
def teacher_hub(request):
    user = request.user
    if not user.is_superuser:
        membership = user.memberships.filter(is_primary=True).first()
        if not membership:
            return HttpResponseForbidden("No primary unit assigned")
        unit = membership.unit
    else:
        unit = None
    
    from .models import EduProfile
    teachers = EduProfile.objects.filter(role_type='TEACHER').select_related('user', 'class_teacher_for').prefetch_related('subjects')
    if unit:
        teachers = teachers.filter(user__memberships__unit=unit)
    return render(request, 'edu/teacher_hub.html', {'teachers': teachers})

@login_required
def staff_hub(request):
    user = request.user
    if not user.is_superuser:
        membership = user.memberships.filter(is_primary=True).first()
        if not membership:
            return HttpResponseForbidden("No primary unit assigned")
        unit = membership.unit
    else:
        unit = None
    
    from .models import EduProfile
    staff = EduProfile.objects.filter(role_type='STAFF').select_related('user')
    if unit:
        staff = staff.filter(user__memberships__unit=unit)
    return render(request, 'edu/staff_hub.html', {'staff': staff})

@login_required
def directory_view(request):
    user = request.user
    if not user.is_superuser:
        membership = user.memberships.filter(is_primary=True).first()
        if not membership:
            return HttpResponseForbidden("No primary unit assigned")
        unit = membership.unit
    else:
        unit = None
    
    from .models import EduProfile
    profiles = EduProfile.objects.all().select_related('user')
    if unit:
        profiles = profiles.filter(user__memberships__unit=unit)
    return render(request, 'edu/directory.html', {'profiles': profiles})

@login_required
def system_view(request):
    user = request.user
    if not user.is_superuser:
        membership = user.memberships.filter(is_primary=True).first()
        if not membership:
            return HttpResponseForbidden("No primary unit assigned")
        unit = membership.unit
    else:
        unit = None
    
    from .models import SchoolConfig
    configs = SchoolConfig.objects.all()
    if unit:
        configs = configs.filter(unit=unit)
    current_config = configs.first() if configs.exists() else None
    
    units = Unit.objects.all()
    if unit:
        units = units.filter(id=unit.id)
        
    return render(request, 'edu/system.html', {
        'units': units,
        'current_config': current_config,
        'logs': []  # Mocked logs for UI purposes
    })


