from django.contrib import admin

from backend.models import (
    SignLog,
    ContactMessage,
    FrequentlyAskedQuestion,
    BookCalendar,
    BlogCategory,
    BlogPost,
    EmailSubscribe,
    PrivacyPolicy,
    TermsAndConditions,
    Session,
    ChatWindow,
    ScreenshotImage,
    WaitList, 
)

@admin.register(WaitList)
class WaitListAdmin(admin.ModelAdmin):
    list_display = ('business_mail', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('business_mail',)

@admin.register(SignLog)
class SignLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'wrong_username', 'ip_address', 'sign_status', 'created_at')
    list_filter = ('sign_status', 'created_at')
    search_fields = ('user__username', 'wrong_username', 'ip_address')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_email',  'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'business_email', 'message')

@admin.register(FrequentlyAskedQuestion)
class FrequentlyAskedQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('question', 'answer') 

@admin.register(BookCalendar)
class BookCalendarAdmin(admin.ModelAdmin):
    list_display = ('event_number', 'start_datetime', 'end_datetime', 'created_at')
    search_fields = ('user__username', 'event_number')

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


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ('version', 'updated_at', 'is_active')
    search_fields = ('version',)
    list_filter = ('is_active', 'updated_at')

@admin.register(TermsAndConditions)
class TermsAndConditionsAdmin(admin.ModelAdmin):
    list_display = ('version', 'updated_at', 'is_active')
    search_fields = ('version',)
    list_filter = ('is_active', 'updated_at')

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username', 'name')

@admin.register(ChatWindow)
class ChatWindowAdmin(admin.ModelAdmin):
    list_display = ('session', 'prompt', 'url', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('session__user__username', 'prompt', 'url')

@admin.register(ScreenshotImage)
class ScreenshotImageAdmin(admin.ModelAdmin):
    list_display = ('chat_window', 'image_order', 'image', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at', 'image_order')
    search_fields = ('chat_window__prompt', 'chat_window__url')
