import re 
from pydantic import validate_email
from rest_framework import serializers 
from django.contrib.auth.models import User 
from django.contrib.auth.password_validation import validate_password 
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError 
import pytz
from backend.models import PrivacyPolicy, SignLog, ContactMessage, FrequentlyAskedQuestion, BookCalendar, EmailSubscribe, BlogCategory, BlogPost, TermsAndConditions, Session, ChatWindow, ScreenshotImage, WaitList 


EMAIL_RE = re.compile(r"^[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+$")

DEFAULT_DISALLOWED_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "live.com", "aol.com", "icloud.com", "mail.com", "gmx.com",
}
DISALLOWED = getattr(settings, "BUSINESS_EMAIL_DISALLOWED_DOMAINS", DEFAULT_DISALLOWED_DOMAINS)

class WaitListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitList
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

    def validate_business_mail(self, value):
        email = (value or "").strip().lower()
        if not EMAIL_RE.match(email):
            raise serializers.ValidationError("Enter a valid email address.")
        domain = email.split("@", 1)[1]
        if domain in DISALLOWED:
            raise serializers.ValidationError("Please use a business email address.")
        return email


class SessionSerializer(serializers.ModelSerializer):
    chat_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = ['id', 'name', 'user', 'chat_count', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'user', 'chat_count', 'created_at', 'updated_at']
    
    def get_chat_count(self, obj):
        return obj.chatwindow_session.filter(is_active=True).count()


class ScreenshotImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreenshotImage
        fields = ['id', 'image', 'image_order', 'created_at']
        read_only_fields = ['id', 'created_at']


class ChatWindowSerializer(serializers.ModelSerializer):
    screenshots = ScreenshotImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatWindow
        fields = ['id', 'session', 'prompt', 'url', 'response', 'analysis_data', 'screenshots', 'created_at', 'updated_at']
        read_only_fields = ['id', 'response', 'analysis_data', 'screenshots', 'created_at', 'updated_at']  
    

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        exclude = ['ip_address', 'user_agent', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']


class FrequentlyAskedQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrequentlyAskedQuestion
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']


class SignUpSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, required=True)
    username = serializers.CharField(required=True)  

    class Meta:
        model = User  
        fields = ['first_name', 'last_name', 'email', 'username', 'password', 'confirm_password']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs 
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value 
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value 
    
    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        user = User.objects.create_user(password=password, **validated_data)
        return user  
        
        
class SignInSerializer(serializers.Serializer):
    username_or_email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)


class BookCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookCalendar
        fields = '__all__'
        read_only_fields = [
            'event_number', 'book_link', 'meet_link', 'user',
            'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted'
        ]

    def validate(self, attrs):
        # Validate timezone
        tz_name = attrs.get('timezone') or (getattr(self.instance, 'timezone', None) if self.instance else None) or settings.TIME_ZONE
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            raise serializers.ValidationError({"timezone": "Invalid timezone."})

        # Allow attendees to be provided as list; store as comma-separated string
        attendees = attrs.get('attendees')
        if isinstance(attendees, list):
            try:
                attrs['attendees'] = ','.join(attendees)
            except Exception:
                raise serializers.ValidationError({"attendees": "Must be a list of email strings or a comma-separated string."})

        # Validate time ordering if both provided (end may be omitted; view will default to +1h)
        start_dt = attrs.get('start_datetime')
        end_dt = attrs.get('end_datetime')
        if start_dt and end_dt and start_dt >= end_dt:
            raise serializers.ValidationError({"end_datetime": "End time must be after start time."})

        # Optional: prevent booking date in the past when explicit date provided
        now_tz = timezone.now().astimezone(tz)
        date_value = attrs.get('date')
        if date_value is not None and date_value < now_tz.date():
            raise serializers.ValidationError({"date": "The date cannot be in the past for the booking timezone."})

        return super().validate(attrs)
    


class EmailSubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSubscribe
        exclude = ['user', 'subscribed_at', 'is_active', 'deleted']


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        exclude = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']


class BlogPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        exclude = ['status', 'published_at', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']


class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        exclude = ['version', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']


class TermsAndConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditions
        exclude = ['version', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']


