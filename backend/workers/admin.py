from django.contrib import admin
from .models import Employer, Worker


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'plan', 'preferred_language', 'created_at']
    list_filter = ['plan', 'preferred_language']
    search_fields = ['first_name', 'last_name', 'email']


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'employer', 'salary', 'is_active', 'start_date']
    list_filter = ['role', 'is_active']
    search_fields = ['first_name', 'last_name', 'nickname']
