import uuid
import os 
from django.db import models
from django.contrib.auth.models import User 
from django.conf import settings 
from django.utils import timezone
from django.utils.text import slugify 
from ckeditor_uploader.fields import RichTextUploadingField 

class SignLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    wrong_username = models.CharField(max_length=150, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    sign_status = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return f"SignLog - {self.user.username if self.user else 'Unknown'} - {self.created_at}" 



class ContactMessage(models.Model):

    INVESTMENT_STAGES_CHOICE = (
        ("BOOTSTRAPPED", "Bootsrapped or Self-funded"), 
        ("PRE-SEED", "Pre-Seed"), 
        ("SEED", "Seed"), 
        ("SERIES_A", "Series A"), 
        ("SERIES_B", "Series B"), 
        ("SERIES_C", "Series C"), 
        ("SERIES_D", "Series D"), 
        ("IPO", "IPO")
    )

    industry = models.CharField(max_length=255, null=True, blank=True) 
    investment_stage = models.CharField(max_length=50, choices=INVESTMENT_STAGES_CHOICE, null=True, blank=True)   

    about = models.TextField(null=True, blank=True) 
    current_problem = models.TextField(null=True, blank=True) 
    interests = models.JSONField(default=list, blank=True)
    budget = models.CharField(max_length=255, null=True, blank=True)

    name = models.CharField(max_length=255)
    business_email = models.EmailField(max_length=255, null=True, blank=True) 

    # metadata 
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='contact_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='contact_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        ordering = ['-created_at']
    

class FrequentlyAskedQuestion(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='faq_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='faq_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def __str__(self):
        return self.question 
    
    class Meta:
        ordering = ['-created_at']
    
class BookCalendar(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    event_number = models.IntegerField(null=True, blank=True)

    full_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)

    summary = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    attendees = models.TextField(null=True, blank=True)  # Comma-separated emails
    
    book_link = models.URLField(null=True, blank=True)
    meet_link = models.URLField(null=True, blank=True)
    timezone = models.CharField(max_length=100, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    reminders = models.BooleanField(default=False)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='calendar_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='calendar_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def save(self, *args, **kwargs):
        if not self.event_number:
            # Safely fetch the highest existing event_number (ignore NULLs)
            last_event = BookCalendar.objects.filter(event_number__isnull=False).order_by('-event_number').first()
            self.event_number = (last_event.event_number + 1) if last_event and last_event.event_number is not None else 1

        if not self.date and self.start_datetime:
            self.date = self.start_datetime.date()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"BookingCalendar  - {self.event_number} "

    class Meta:
        ordering = ['-created_at']
    

class EmailSubscribe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def __str__(self):
        return self.email

    class Meta:
        ordering = ['-subscribed_at']

class BlogCategory(models.Model):
    name = models.CharField(max_length=512, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True) 
    description = models.TextField(null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blogcategory_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blogcategory_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class BlogPost(models.Model):

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('scheduled', 'Scheduled'),
        ('archived', 'Archived'),
    ] 

    category = models.ForeignKey(BlogCategory, on_delete=models.DO_NOTHING, related_name='posts')
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=512, null=True, blank=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True) 

    content = RichTextUploadingField()

    meta_title = models.CharField(max_length=255, null=True, blank=True)
    meta_description = models.TextField(null=True, blank=True) 

    cover_image = models.ImageField(upload_to='blog_covers/', null=True, blank=True)
    image = models.ImageField(upload_to='blog_images/', null=True, blank=True) 

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blogpost_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blogpost_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_at']



class PrivacyPolicy(models.Model):
    version = models.CharField(max_length=50, null=True, blank=True)
    content = RichTextUploadingField()

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='privacypolicy_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='privacypolicy_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"PrivacyPolicy - {self.created_at}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Privacy Policy"


class TermsAndConditions(models.Model):
    version = models.CharField(max_length=50, null=True, blank=True) 
    content = RichTextUploadingField()

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='terms_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='terms_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"TermsAndConditions - {self.created_at}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Terms and Conditions" 


class WaitList(models.Model):
    business_mail = models.EmailField(max_length=255) 

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='waitlist_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='waitlist_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def __str__(self):
        return self.business_mail 
    
    class Meta:
        ordering = ['-created_at'] 


class Session(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) 
    name = models.CharField(max_length=255, null=True, blank=True) 

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='session_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='session_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name 

    class Meta:
        ordering = ['-created_at']

class ChatWindow(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='chatwindow_session')  
    prompt = models.TextField(null=True, blank=True) 
    url = models.URLField(null=True, blank=True) 

    response = models.TextField(null=True, blank=True)  
    
    # Store structured app analysis data (sentiment, ratings, issues, recommendations, etc.)
    analysis_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def __str__(self):
        return self.prompt if self.prompt else f"ChatWindow {self.id}"

    class Meta:
        ordering = ['-created_at']


class ScreenshotImage(models.Model):
    chat_window = models.ForeignKey(ChatWindow, on_delete=models.CASCADE, related_name='screenshots')
    image = models.ImageField(upload_to='agent/')
    image_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Screenshot {self.image_order} for {self.chat_window}"

    class Meta:
        ordering = ['image_order', '-created_at']


def video_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('videos/', filename) 
        

class Videos(models.Model):
    project_name = models.CharField(max_length=255) 
    slug = models.SlugField(max_length=100, unique=True, blank=True) 
    video_file = models.FileField(upload_to=video_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True) 

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_created_by') 
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='video_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    is_active = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False) 

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.project_name)
        super().save(*args, **kwargs) 

    class Meta:
        ordering = ['-created_at'] 

    def __str__(self):
        return self.project_name 
