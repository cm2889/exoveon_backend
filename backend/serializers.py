from rest_framework import serializers 
from django.contrib.auth.models import User 
from django.contrib.auth.password_validation import validate_password 

from backend.models import SignLog, ContactMessage, FrequentlyAskedQuestion, BookCalendar, BookMeet 


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
    """
    Serializer for BookCalendar model with Google Calendar integration
    """
    # Additional fields for creating Google Calendar event
    summary = serializers.CharField(write_only=True, max_length=255, help_text="Event title/summary")
    description = serializers.CharField(write_only=True, required=False, allow_blank=True, help_text="Event description")
    timezone = serializers.CharField(write_only=True, required=False, default='UTC', help_text="Timezone (e.g., 'America/New_York')")
    attendees = serializers.ListField(
        child=serializers.EmailField(),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text="List of attendee email addresses"
    )
    location = serializers.CharField(write_only=True, required=False, allow_blank=True, help_text="Event location")
    reminders = serializers.BooleanField(write_only=True, required=False, default=True, help_text="Enable reminders")
    
    # Read-only fields from model
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = BookCalendar
        fields = [
            'id', 'user', 'event_id', 'html_link', 'start_datetime', 'end_datetime', 
            'created_at', 'summary', 'description', 'timezone', 'attendees', 
            'location', 'reminders'
        ]
        read_only_fields = ['id', 'user', 'event_id', 'html_link', 'created_at']
    
    def validate(self, attrs):
        """Validate that end_datetime is after start_datetime"""
        if attrs['start_datetime'] >= attrs['end_datetime']:
            raise serializers.ValidationError({
                'end_datetime': 'End time must be after start time.'
            })
        return attrs


class BookMeetSerializer(serializers.ModelSerializer):
    """
    Serializer for BookMeet model with Google Meet integration
    """
    # Additional fields for creating Google Meet
    summary = serializers.CharField(write_only=True, max_length=255, help_text="Meeting title")
    description = serializers.CharField(write_only=True, required=False, allow_blank=True, help_text="Meeting description")
    timezone = serializers.CharField(write_only=True, required=False, default='UTC', help_text="Timezone (e.g., 'America/New_York')")
    attendees = serializers.ListField(
        child=serializers.EmailField(),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text="List of attendee email addresses"
    )
    send_notifications = serializers.BooleanField(write_only=True, required=False, default=True, help_text="Send email notifications to attendees")
    reminders = serializers.BooleanField(write_only=True, required=False, default=True, help_text="Enable reminders")
    
    # Read-only fields from model
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = BookMeet
        fields = [
            'id', 'user', 'meet_link', 'start_datetime', 'end_datetime', 
            'created_at', 'summary', 'description', 'timezone', 'attendees',
            'send_notifications', 'reminders'
        ]
        read_only_fields = ['id', 'user', 'meet_link', 'created_at']
    
    def validate(self, attrs):
        """Validate that end_datetime is after start_datetime"""
        if attrs['start_datetime'] >= attrs['end_datetime']:
            raise serializers.ValidationError({
                'end_datetime': 'End time must be after start time.'
            })
        return attrs

