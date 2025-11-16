from django.contrib import admin

from backend.models import SignLog, ContactMessage, FrequentlyAskedQuestion, BookCalendar, BookMeet


@admin.register(SignLog)
class SignLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'wrong_username', 'ip_address', 'sign_status', 'created_at')
    list_filter = ('sign_status', 'created_at')
    search_fields = ('user__username', 'wrong_username', 'ip_address')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email',  'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('full_name', 'email', 'message')

@admin.register(FrequentlyAskedQuestion)
class FrequentlyAskedQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('question', 'answer') 

@admin.register(BookCalendar)
class BookCalendarAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_id', 'start_datetime', 'end_datetime', 'created_at')
    search_fields = ('user__username', 'event_id')

@admin.register(BookMeet)
class BookMeetAdmin(admin.ModelAdmin):
    list_display = ('user', 'meet_link', 'start_datetime', 'end_datetime', 'created_at')
    search_fields = ('user__username', 'meet_link')