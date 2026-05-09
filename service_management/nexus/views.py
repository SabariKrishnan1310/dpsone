from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from sterling_core.models import Organization, Unit, SterlingUser, Membership
from django.contrib import messages
from django.contrib.auth.models import User

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def nexus_dashboard(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_org':
            name = request.POST.get('org_name')
            Organization.objects.create(name=name, slug=name.lower().replace(' ', '-'))
            messages.success(request, f'Organization {name} created.')
            
        elif action == 'create_unit':
            name = request.POST.get('unit_name')
            org_id = request.POST.get('org_id')
            org = Organization.objects.get(id=org_id)
            Unit.objects.create(name=name, unit_code=name[:3].upper(), organization=org)
            messages.success(request, f'Unit {name} created.')
            
        elif action == 'onboard_principal':
            username = request.POST.get('username')
            password = request.POST.get('password')
            unit_id = request.POST.get('unit_id')
            unit = Unit.objects.get(id=unit_id)
            
            # Create user with is_staff=True for admin access
            user = SterlingUser.objects.create_user(username=username, password=password)
            user.is_staff = True
            user.save()
            
            # Create Membership with MANAGER role
            Membership.objects.create(user=user, unit=unit, role='MANAGER', is_primary=True)
            messages.success(request, f'Principal {username} onboarded for {unit.name}.')
            
        return redirect('nexus:dashboard')

    context = {
        'orgs': Organization.objects.all(),
        'units': Unit.objects.all(),
    }
    return render(request, 'nexus/dashboard.html', context)
