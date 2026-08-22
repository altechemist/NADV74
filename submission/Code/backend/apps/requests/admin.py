from django.contrib import admin

from .models import Category, Notification, RequestHistory, ServiceRequest


class RequestHistoryInline(admin.TabularInline):
    model = RequestHistory
    extra = 0
    readonly_fields = ("entry_type", "changed_by", "from_status", "to_status", "comment", "created_at")
    can_delete = False


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("reference", "title", "category", "priority", "status", "source", "created_at")
    list_filter = ("status", "priority", "source", "category")
    search_fields = ("reference", "title", "location")
    inlines = [RequestHistoryInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "active")


admin.site.register(Notification)
