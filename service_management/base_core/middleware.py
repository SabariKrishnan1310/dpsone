from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from django.urls import reverse

class RoleRoutingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip routing for logout and auth-related paths
        if request.path.startswith('/dashboard/edu/logout') or request.path.startswith('/dashboard/edu/login'):
            return self.get_response(request)
        
        if request.user.is_authenticated:
            # Nexus Security
            if request.path.startswith('/nexus/'):
                if not request.user.is_superuser:
                    return HttpResponseForbidden("Access Denied: Superuser Required")
            
            # Superuser -> Nexus
            elif request.user.is_superuser and not request.path.startswith('/admin/'):
                if request.path != reverse('nexus:dashboard'):
                    return redirect(reverse('nexus:dashboard'))
            
            # Principal -> Edu Dashboard
            elif request.user.memberships.filter(role='MANAGER').exists():
                if request.path == '/' or request.path.startswith('/edu/'):
                    if request.path != reverse('edu:dashboard'):
                        return redirect(reverse('edu:dashboard'))
            
            # Teacher/Staff -> Schedule
            elif hasattr(request.user, 'edu_profile') and request.user.edu_profile.role_type in ['TEACHER', 'STAFF']:
                 if request.path == '/':
                    return redirect(reverse('edu:schedule'))
        
        return self.get_response(request)
