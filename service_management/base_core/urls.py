from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.http import JsonResponse
from django.db import connection
import redis

def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        postgres_ok = True
    except Exception:
        postgres_ok = False
    
    try:
        r = redis.Redis(host='redis', port=6379, db=0)
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    
    status = 200 if (postgres_ok and redis_ok) else 503
    return JsonResponse({
        'status': 'healthy' if status == 200 else 'unhealthy',
        'postgres': 'ok' if postgres_ok else 'error',
        'redis': 'ok' if redis_ok else 'error',
    }, status=status)

# Redirect old /edu/identity/ to dashboard with modal
def identity_redirect(request):
    return redirect('edu:dashboard')

urlpatterns = [
    path('health/', health_check, name='health'),
    path('', lambda req: redirect('/dashboard/edu/')),
    path('admin/', admin.site.urls),
    path('dashboard/edu/', include('edu.urls')),
    path('dashboard/fnb/', include('fnb.urls')),
    path('nexus/', include('nexus.urls')),
    # Legacy redirects
    path('edu/identity/', identity_redirect),
    path('edu/login/', lambda req: redirect('/dashboard/edu/login/')),
    path('edu/logout/', lambda req: redirect('/dashboard/edu/logout/')),
]