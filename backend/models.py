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
    