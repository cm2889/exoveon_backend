from django.db import models
from django.contrib.auth.models import User 

class SignLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    wrong_username = models.CharField(max_length=150, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    sign_status = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return f"SignLog - {self.user.username if self.user else 'Unknown'} - {self.created_at}" 
    

class ContactMessage(models.Model):
    full_name = models.CharField(max_length=255)
    
    email = models.EmailField(max_length=255, null=True, blank=True) 
    phone = models.CharField(max_length=20, null=True, blank=True) 
    subject = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True) 

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
        return f"ContactMessage - {self.subject} from {self.full_name}"
    

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