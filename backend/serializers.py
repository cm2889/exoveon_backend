from rest_framework import serializers 
from django.contrib.auth.models import User 
from django.contrib.auth.password_validation import validate_password 
from django.conf import settings
from django.utils import timezone
import pytz
from backend.models import SignLog, ContactMessage, FrequentlyAskedQuestion, BookCalendar, BookMeet, EmailSubscribe


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

class FrequentlyAskedQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrequentlyAskedQuestion
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']


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
        read_only_fields = ['event_id', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

    def validate(self, attrs):

        tz_name = attrs.get('timezone') or (getattr(self.instance, 'timezone', None) if self.instance else None) or settings.TIME_ZONE

        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            raise serializers.ValidationError({"timezone": "Invalid timezone."})

        # Current moment in the booking timezone
        now_tz = timezone.now().astimezone(tz)

        # Validate date (keep it as date object)
        date_value = attrs.get('date')
        if date_value is not None:
            if date_value < now_tz.date():
                raise serializers.ValidationError({"date": "The date cannot be in the past for the booking timezone."})
            
        return super().validate(attrs)
    
    
class BookMeetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookMeet
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']


class EmailSubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSubscribe
        fields = '__all__'
        read_only_fields = ['user', 'subscribed_at']

