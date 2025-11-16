from django.utils import timezone 
from datetime import timedelta
from django.contrib.auth import authenticate 
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required 
from rest_framework.decorators import api_view 
from rest_framework.views import APIView 
from rest_framework.response import Response
from rest_framework import status 
from rest_framework import permissions 
from rest_framework import generics 
from rest_framework import viewsets 
from rest_framework.exceptions import PermissionDenied 
from rest_framework import permissions 
from rest_framework.decorators import api_view, permission_classes, action 
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework_simplejwt.views import TokenObtainPairView 
from rest_framework_simplejwt.tokens import RefreshToken, TokenError 

from django.contrib.auth.models import User 

from backend.serializers import (
    SignUpSerializer, SignInSerializer, ContactMessageSerializer, 
    FrequentlyAskedQuestionSerializer, BookCalendarSerializer,
    BookMeetSerializer
)
from backend.models import SignLog, ContactMessage, FrequentlyAskedQuestion, BookCalendar, BookMeet 
from core.paginations import DynamicPagination 
from core.exclude_csrf import CsrfExemptSessionAuthentication 
from core.permissions import IsSuperUserOrPostAndRead, IsOwnerOrReadOnly

from django.conf import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json


@api_view(['POST'])
def sign_up(request):
    serializer = SignUpSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def sign_in(request):
    serializer = SignInSerializer(data=request.data)

    if request.method == 'POST':
        username_or_email = serializer.initial_data.get('username_or_email')
        password = serializer.initial_data.get('password')
        user_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR') 

        if not username_or_email or not password:
            return Response({'error': 'Username/Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST) 
        
        if username_or_email:
            if "@" in username_or_email:
                user = User.objects.filter(email=username_or_email).first() 
            else:
                user = User.objects.filter(username=username_or_email).first()
        else:
            SignLog.objects.create(
                user=None,
                wrong_username=None,
                ip_address=user_ip,
                sign_status=False,
            )
            return Response({'error': 'Username or email must be provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not user or not user.check_password(password):
            SignLog.objects.create(
                user=user if user else None,
                wrong_username=username_or_email if not user else None,
                ip_address=user_ip,
                sign_status=False,
            )
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = authenticate(username=user.username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            SignLog.objects.create(
                user=user,
                wrong_username=None,
                ip_address=user_ip,
                sign_status=True,
            )

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sign_out(request):
    refresh_token = request.data.get('refresh')

    if not refresh_token:
        return Response({'error': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError:
        return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'message': 'User signed out successfully.'}, status=status.HTTP_200_OK)


class FrequentlyAskedQuestionViewSet(viewsets.ModelViewSet):
    queryset = FrequentlyAskedQuestion.objects.filter(is_active=True) 
    serializer_class = FrequentlyAskedQuestionSerializer
    permission_classes = [permissions.AllowAny] 
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user if self.request.user.is_authenticated else None,
        )
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user if self.request.user.is_authenticated else None)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response({'message': 'FAQ deleted successfully'}, status=status.HTTP_200_OK)



class ContactMessageViewSet(viewsets.ModelViewSet):
    queryset = ContactMessage.objects.filter(is_active=True) 
    serializer_class = ContactMessageSerializer
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.AllowAny] 
    pagination_class = DynamicPagination 

    def perform_create(self, serializer):
        user_ip = self.request.META.get('HTTP_X_FORWARDED_FOR') or self.request.META.get('REMOTE_ADDR') 
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')

        serializer.save(
            created_by=self.request.user if self.request.user.is_authenticated else None,
            ip_address=user_ip,
            user_agent=user_agent
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user if self.request.user.is_authenticated else None)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response({'message': 'Contact message deleted successfully'}, status=status.HTTP_200_OK)
    


class BookCalendarViewSet(viewsets.ModelViewSet):
    queryset = BookCalendar.objects.all()
    serializer_class = BookCalendarSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination

    def get_authenticate_header(self, request):
        return BookCalendar.objects.filter(is_active=True) 
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
        return super().perform_create(serializer) 
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user if self.request.user.is_authenticated else None)
        return super().perform_update(serializer) 
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response({'message': 'Calendar booking deleted successfully'}, status=status.HTTP_200_OK)
    

class BookMeetViewSet(viewsets.ModelViewSet):
    queryset = BookMeet.objects.all()
    serializer_class = BookMeetSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination

    def get_authenticate_header(self, request):
        return BookMeet.objects.filter(is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user if self.request.user.is_authenticated else None)
        return super().perform_update(serializer)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response({'message': 'Meeting booking deleted successfully'}, status=status.HTTP_200_OK)




# class BookCalendarViewSet(viewsets.ModelViewSet):
#     queryset = BookCalendar.objects.all()
#     serializer_class = BookCalendarSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
#     pagination_class = DynamicPagination
    
#     def get_queryset(self):
#         """Return bookings only for the authenticated user"""
#         return BookCalendar.objects.filter(user=self.request.user).order_by('-created_at')
    
#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
        
#         if not serializer.is_valid():
#             return Response({ 'success': False,  'errors': serializer.errors  }, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             data = serializer.validated_data
            
#             credentials_data = request.session.get('google_credentials')
#             print(f"Debug message: {credentials_data}")
            
#             if not credentials_data:
#                 flow = Flow.from_client_config(
#                     {
#                         "web": {
#                             "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
#                             "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
#                             "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#                             "token_uri": "https://oauth2.googleapis.com/token",
#                             "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI]
#                         }
#                     },
#                     scopes=['https://www.googleapis.com/auth/calendar']
#                 )

#                 flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
#                 authorization_url, state = flow.authorization_url( access_type='offline',  include_granted_scopes='true' )
                
#                 return Response({
#                     'success': False,
#                     'message': 'Google authentication required',
#                     'auth_url': authorization_url,
#                     'state': state
#                 }, status=status.HTTP_401_UNAUTHORIZED)
            
#             credentials = Credentials(**credentials_data)
            
#             # Build Google Calendar service
#             service = build('calendar', 'v3', credentials=credentials)
            
#             # Prepare event data
#             tz = data.pop('timezone', 'UTC')
#             event = {
#                 'summary': data.pop('summary'),
#                 'description': data.pop('description', ''),
#                 'start': {
#                     'dateTime': data['start_datetime'].isoformat(),
#                     'timeZone': tz,
#                 },
#                 'end': {
#                     'dateTime': data['end_datetime'].isoformat(),
#                     'timeZone': tz,
#                 },
#             }
            
#             # Add location if provided
#             location = data.pop('location', None)
#             if location:
#                 event['location'] = location
            
#             # Add attendees if provided
#             attendees = data.pop('attendees', None)
#             if attendees:
#                 event['attendees'] = [{'email': email} for email in attendees]
            
#             # Add reminders
#             if data.pop('reminders', True):
#                 event['reminders'] = {
#                     'useDefault': False,
#                     'overrides': [
#                         {'method': 'email', 'minutes': 24 * 60},
#                         {'method': 'popup', 'minutes': 30},
#                     ],
#                 }
            
#             # Create the event in Google Calendar
#             created_event = service.events().insert(
#                 calendarId='primary',
#                 body=event,
#                 sendUpdates='all'
#             ).execute()
            
#             # Save to database
#             booking = BookCalendar.objects.create(
#                 user=request.user,
#                 event_id=created_event.get('id'),
#                 html_link=created_event.get('htmlLink'),
#                 start_datetime=data['start_datetime'],
#                 end_datetime=data['end_datetime']
#             )
            
#             response_serializer = self.get_serializer(booking)
#             return Response({
#                 'success': True,
#                 'data': response_serializer.data,
#                 'message': 'Calendar event created successfully'
#             }, status=status.HTTP_201_CREATED)
            
#         except HttpError as error:
#             return Response({
#                 'success': False,
#                 'message': f'Google Calendar API error: {str(error)}'
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
#         except Exception as e:
#             return Response({
#                 'success': False,
#                 'message': f'Error creating calendar event: {str(e)}'
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     @action(detail=False, methods=['get'], url_path='sample-payload')
#     def sample_payload(self, request):
#         now = timezone.now()
#         payload = {
#             "summary": "Team Sync",
#             "description": "Weekly sync",
#             "start_datetime": (now + timedelta(hours=1)).isoformat(),
#             "end_datetime": (now + timedelta(hours=2)).isoformat(),
#             "timezone": "UTC",
#             "attendees": [],
#             "location": "Virtual",
#             "reminders": True
#         }
#         return Response(payload, status=status.HTTP_200_OK)


# class BookMeetViewSet(viewsets.ModelViewSet):
#     queryset = BookMeet.objects.all()
#     serializer_class = BookMeetSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
#     pagination_class = DynamicPagination
    
#     def get_queryset(self):
#         """Return bookings only for the authenticated user"""
#         return BookMeet.objects.filter(user=self.request.user).order_by('-created_at')
    
#     def create(self, request, *args, **kwargs):
#         """Create a Google Meet in Google Calendar and save to database"""
#         serializer = self.get_serializer(data=request.data)
        
#         if not serializer.is_valid():
#             return Response({
#                 'success': False,
#                 'errors': serializer.errors
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             data = serializer.validated_data
            
#             # Check if user has Google OAuth credentials stored in session
#             credentials_data = request.session.get('google_credentials')
            
#             if not credentials_data:
#                 # Return OAuth URL for user to authenticate
#                 flow = Flow.from_client_config(
#                     {
#                         "web": {
#                             "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
#                             "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
#                             "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#                             "token_uri": "https://oauth2.googleapis.com/token",
#                             "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI]
#                         }
#                     },
#                     scopes=['https://www.googleapis.com/auth/calendar']
#                 )
#                 flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
#                 authorization_url, state = flow.authorization_url(
#                     access_type='offline',
#                     # Google expects lowercase 'true'/'false' strings here
#                     include_granted_scopes='true'
#                 )
                
#                 return Response({
#                     'success': False,
#                     'message': 'Google authentication required',
#                     'auth_url': authorization_url,
#                     'state': state
#                 }, status=status.HTTP_401_UNAUTHORIZED)
            
#             # Create credentials from stored data
#             credentials = Credentials(**credentials_data)
            
#             # Build Google Calendar service
#             service = build('calendar', 'v3', credentials=credentials)
            
#             # Prepare event data with Google Meet conference
#             tz = data.pop('timezone', 'UTC')
#             event = {
#                 'summary': data.pop('summary'),
#                 'description': data.pop('description', ''),
#                 'start': {
#                     'dateTime': data['start_datetime'].isoformat(),
#                     'timeZone': tz,
#                 },
#                 'end': {
#                     'dateTime': data['end_datetime'].isoformat(),
#                     'timeZone': tz,
#                 },
#                 'conferenceData': {
#                     'createRequest': {
#                         'requestId': f"meet-{request.user.id}-{timezone.now().timestamp()}",
#                         'conferenceSolutionKey': {
#                             'type': 'hangoutsMeet'
#                         }
#                     }
#                 }
#             }
            
#             # Add attendees if provided
#             attendees = data.pop('attendees', None)
#             if attendees:
#                 event['attendees'] = [{'email': email} for email in attendees]
            
#             # Add reminders
#             if data.pop('reminders', True):
#                 event['reminders'] = {
#                     'useDefault': False,
#                     'overrides': [
#                         {'method': 'email', 'minutes': 24 * 60},
#                         {'method': 'popup', 'minutes': 30},
#                     ],
#                 }
            
#             # Create the event with conference data
#             send_updates = 'all' if data.pop('send_notifications', True) else 'none'
            
#             created_event = service.events().insert(
#                 calendarId='primary',
#                 body=event,
#                 conferenceDataVersion=1,
#                 sendUpdates=send_updates
#             ).execute()
            
#             # Extract Google Meet link
#             meet_link = None
#             if 'conferenceData' in created_event:
#                 entry_points = created_event['conferenceData'].get('entryPoints', [])
#                 for entry_point in entry_points:
#                     if entry_point.get('entryPointType') == 'video':
#                         meet_link = entry_point.get('uri')
#                         break
            
#             # Save to database
#             booking = BookMeet.objects.create(
#                 user=request.user,
#                 meet_link=meet_link or '',
#                 start_datetime=data['start_datetime'],
#                 end_datetime=data['end_datetime']
#             )
            
#             response_serializer = self.get_serializer(booking)
#             return Response({
#                 'success': True,
#                 'data': response_serializer.data,
#                 'message': 'Google Meet created successfully'
#             }, status=status.HTTP_201_CREATED)
            
#         except HttpError as error:
#             return Response({
#                 'success': False,
#                 'message': f'Google Calendar API error: {str(error)}'
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
#         except Exception as e:
#             return Response({
#                 'success': False,
#                 'message': f'Error creating Google Meet: {str(e)}'
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     @action(detail=False, methods=['get'], url_path='sample-payload')
#     def sample_payload(self, request):
#         now = timezone.now()
#         payload = {
#             "summary": "Client Call",
#             "description": "Discuss requirements",
#             "start_datetime": (now + timedelta(hours=3)).isoformat(),
#             "end_datetime": (now + timedelta(hours=4)).isoformat(),
#             "timezone": "UTC",
#             "attendees": [],
#             "send_notifications": True,
#             "reminders": True
#         }
#         return Response(payload, status=status.HTTP_200_OK)


# @api_view(['GET'])
# def google_oauth_callback(request):
#     """
#     Handle Google OAuth callback and store credentials
    
#     GET /api/google-oauth-callback/?code=...&state=...
#     """
#     try:
#         code = request.GET.get('code')
        
#         if not code:
#             return Response({
#                 'success': False,
#                 'message': 'Authorization code not found'
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         # Exchange authorization code for credentials
#         flow = Flow.from_client_config(
#             {
#                 "web": {
#                     "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
#                     "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
#                     "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#                     "token_uri": "https://oauth2.googleapis.com/token",
#                     "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI]
#                 }
#             },
#             scopes=['https://www.googleapis.com/auth/calendar']
#         )
#         flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
#         flow.fetch_token(code=code)
        
#         # Store credentials in session
#         credentials = flow.credentials
#         request.session['google_credentials'] = {
#             'token': credentials.token,
#             'refresh_token': credentials.refresh_token,
#             'token_uri': credentials.token_uri,
#             'client_id': credentials.client_id,
#             'client_secret': credentials.client_secret,
#             'scopes': credentials.scopes
#         }
        
#         return Response({
#             'success': True,
#             'message': 'Google OAuth authentication successful'
#         }, status=status.HTTP_200_OK)
        
#     except Exception as e:
#         return Response({
#             'success': False,
#             'message': f'OAuth callback error: {str(e)}'
#         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)