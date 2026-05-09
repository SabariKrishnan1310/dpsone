from django.urls import path
from . import views

app_name = 'edu'

urlpatterns = [
    # Global Dashboard
    path('', views.dashboard, name='dashboard'),
    path('api/dashboard-data/', views.dashboard_data, name='dashboard-data'),
    
    # Context-Aware Identity Modal Creation
    path('identity/', views.IdentityCreateView.as_view(), name='identity'),
    
    # Hubs (Billion-Dollar Architecture)
    path('student-hub/', views.student_hub, name='student-hub'),
    path('teacher-hub/', views.teacher_hub, name='teacher-hub'),
    path('staff-hub/', views.staff_hub, name='staff-hub'),
    path('directory/', views.directory_view, name='directory'),
    path('system/', views.system_view, name='system'),
    
    # Auth
    path('settings/', views.settings_view, name='settings'),
    path('login/', views.edu_login, name='login'),
    path('logout/', views.edu_logout, name='logout'),
    path('staff/', views.StaffListView.as_view(), name='staff'),
    path('students/', views.StudentListView.as_view(), name='students'),
]