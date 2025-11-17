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
    name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    slug = serializers.CharField(write_only=True, required=False, allow_blank=True)
    internal_note = serializers.CharField(write_only=True, required=False, allow_blank=True)
    description_plain = serializers.CharField(write_only=True, required=False, allow_blank=True)
    kind = serializers.CharField(write_only=True, required=False, allow_blank=True)
    duration = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = BookCalendar
        fields = '__all__'
        read_only_fields = ['event_id', 'created_by', 'updated_by', 'created_at', 'updated_at', 'is_active', 'deleted']

    def validate(self, attrs):
        calendly_keys = {k: attrs.get(k) for k in ['kind', 'duration']}
        
        if any(calendly_keys.values()):
            kind = calendly_keys.get('kind') or ''
            if kind and kind not in { 'solo', 'group' }:
                raise serializers.ValidationError({"kind": "Invalid Calendly event type kind. Use 'solo' or 'group'."})
            
            duration = calendly_keys.get('duration')
            if duration is not None:
                if duration <= 0 or duration > 480:  
                    raise serializers.ValidationError({"duration": "Duration must be between 1 and 480 minutes."})

        tz_name = attrs.get('timezone') or (getattr(self.instance, 'timezone', None) if self.instance else None) or settings.TIME_ZONE

        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            raise serializers.ValidationError({"timezone": "Invalid timezone."})

        now_tz = timezone.now().astimezone(tz)

        date_value = attrs.get('date')
        if date_value is not None:
            if date_value < now_tz.date():
                raise serializers.ValidationError({"date": "The date cannot be in the past for the booking timezone."})
            
        return super().validate(attrs)

    # Ensure non-model, write-only Calendly fields are not passed to the model layer
    _transient_calendly_fields = (
        'name', 'slug', 'internal_note', 'description_plain', 'kind', 'duration', 'owner'
    )

    def _strip_transient_fields(self, data: dict) -> dict:
        for k in self._transient_calendly_fields:
            data.pop(k, None)
        return data

    def create(self, validated_data):
        validated_data = self._strip_transient_fields(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._strip_transient_fields(validated_data)
        return super().update(instance, validated_data)
    
    
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

