from django.contrib import admin

from backend.models import (
    SignLog,
    ContactMessage,
    FrequentlyAskedQuestion,
    BookCalendar,
    BookMeet,
    BlogCategory,
    BlogPost,
    EmailSubscribe
)


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
    list_display = ('event_number', 'start_datetime', 'end_datetime', 'created_at')
    search_fields = ('user__username', 'event_number')

@admin.register(BookMeet)
class BookMeetAdmin(admin.ModelAdmin):
    list_display = ('user', 'meet_link', 'start_datetime', 'end_datetime', 'created_at')
    search_fields = ('user__username', 'meet_link')

@admin.register(EmailSubscribe)
class EmailSubscribeAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at', 'is_active')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email',)


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ('is_active',)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'category', 'status', 'published_at', 'created_at', 'is_active'
    )
    search_fields = ('title', 'subtitle', 'slug')
    prepopulated_fields = {"slug": ("title",)}
    list_filter = ('status', 'is_active', 'category')
    autocomplete_fields = ('category',)