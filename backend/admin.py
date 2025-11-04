from django.contrib import admin

from backend.models import SignLog, ContactMessage, FrequentlyAskedQuestion


@admin.register(SignLog)
class SignLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'wrong_username', 'ip_address', 'sign_status', 'created_at')
    list_filter = ('sign_status', 'created_at')
    search_fields = ('user__username', 'wrong_username', 'ip_address')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'subject', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('full_name', 'email', 'subject', 'message')

@admin.register(FrequentlyAskedQuestion)
class FrequentlyAskedQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('question', 'answer') 