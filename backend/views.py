import os
import json
import pytz
import asyncio
import json
import traceback
import asyncio
import pytz
import requests
from django.utils import timezone 
from datetime import timedelta
from pathlib import Path
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
from backend.serializers import SignUpSerializer, SignInSerializer, ContactMessageSerializer, FrequentlyAskedQuestionSerializer, BookCalendarSerializer, EmailSubscribeSerializer, BlogCategorySerializer, BlogPostSerializer, TermsAndConditionsSerializer, PrivacyPolicySerializer, SessionSerializer, ChatWindowSerializer, VideosSerializer, WaitListSerializer, Videos, DeepChatSerializer
from backend.models import SignLog, ContactMessage, FrequentlyAskedQuestion, BookCalendar, EmailSubscribe, BlogCategory, BlogPost, TermsAndConditions, PrivacyPolicy, Session, ChatWindow, ScreenshotImage, WaitList, Videos, DeepChat 

from core.paginations import DynamicPagination 
from core.exclude_csrf import CsrfExemptSessionAuthentication 
from core.permissions import IsSuperUserOrPostAndRead, IsOwnerOrReadOnly, IsOwnerOnly 
from django.conf import settings
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.core.files.base import ContentFile
from agent.brower_agent import screenshot_agent
from agent.app_agent import analyze_app_and_report
from agent.url_detector import detect_url_type, normalize_url
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.db.models import Q
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials


GOOGLE_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

CREDS_FILENAME = 'auth_creds.json'


def _load_default_client_config():
    """Load default client config from auth_creds.json in BASE_DIR."""
    creds_path = os.path.join(settings.BASE_DIR, CREDS_FILENAME)
    if not os.path.exists(creds_path):
        return None
    with open(creds_path, 'r') as f:
        return json.load(f)


def _ensure_client_config(client_config: dict, redirect_uri: str | None):
    """
    Ensure client_config has the proper redirect_uri set.
    If redirect_uri is provided, override the config to use that.
    """
    if not client_config or 'web' not in client_config:
        return None

    if redirect_uri:
        # Overwrite redirect_uris to ensure the same value is used in both steps
        client_config = json.loads(json.dumps(client_config))  # shallow-clone
        web = client_config.setdefault('web', {})
        web['redirect_uris'] = [redirect_uri]

    return client_config


@api_view(['POST'])
def google_auth(request):
    try:
        redirect_uri = request.data.get('redirect_uri')

        client_config = request.data if isinstance(request.data, dict) and 'web' in request.data else None
        if client_config is None:
            client_config = _load_default_client_config()

        if client_config is None:
            return Response({'success': False, 'message': 'Google OAuth client config not provided'}, status=status.HTTP_400_BAD_REQUEST)

        client_config = _ensure_client_config(client_config, redirect_uri)
        if client_config is None:
            return Response({'success': False, 'message': 'Invalid Google OAuth client config'},  status=status.HTTP_400_BAD_REQUEST)

        flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES)
        flow.redirect_uri = client_config['web']['redirect_uris'][0]

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        request.session['google_oauth_client_config'] = client_config
        request.session['google_oauth_state'] = state

        return Response({'success': True, 'auth_url': authorization_url, 'state': state}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'success': False, 'message': f'Error initiating Google OAuth: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def google_auth_callback(request):
    try:
        code = request.GET.get('code')
        state = request.GET.get('state')
        redirect_uri = request.GET.get('redirect_uri')  # optional, helps when session was rotated

        if not code:
            return Response({'success': False, 'message': 'Authorization code missing'}, status=status.HTTP_400_BAD_REQUEST)

        client_config = request.session.get('google_oauth_client_config')
        saved_state = request.session.get('google_oauth_state')

        if not client_config:
            client_config = _load_default_client_config()
            if client_config is None:
                return Response({'success': False, 'message': 'OAuth client config missing'}, status=status.HTTP_400_BAD_REQUEST)

        client_config = _ensure_client_config(client_config, redirect_uri)

        if client_config is None:
            return Response({'success': False, 'message': 'Invalid OAuth client config'}, status=status.HTTP_400_BAD_REQUEST)

        if saved_state and state and saved_state != state:
            return Response({'success': False, 'message': 'Invalid OAuth state'}, status=status.HTTP_400_BAD_REQUEST)

        flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES)
        flow.redirect_uri = client_config['web']['redirect_uris'][0]
        flow.fetch_token(code=code)

        credentials = flow.credentials

        userinfo_resp = requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            params={'alt': 'json'},
            headers={'Authorization': f'Bearer {credentials.token}'}
        )

        if userinfo_resp.status_code != 200:
            return Response({'success': False, 'message': 'Failed to fetch Google user info'}, status=status.HTTP_400_BAD_REQUEST)

        userinfo = userinfo_resp.json()
        email = userinfo.get('email')
        given_name = userinfo.get('given_name') or ''
        family_name = userinfo.get('family_name') or ''
        full_name = userinfo.get('name') or f'{given_name} {family_name}'.strip()

        if not email:
            return Response({'success': False, 'message': 'Google account email not available'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()

        if not user:
            base_username = email.split('@')[0]
            username = base_username
            i = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{i}"
                i += 1

            user = User.objects.create(username=username, email=email)
            user.set_unusable_password()
            user.first_name = given_name or (full_name.split(' ')[0] if full_name else '')
            user.last_name = family_name or (full_name.split(' ')[-1] if full_name else '')
            user.save()

        refresh = RefreshToken.for_user(user)

        request.session['google_credentials'] = {
            'token': credentials.token,
            'refresh_token': getattr(credentials, 'refresh_token', None),
            'token_uri': getattr(credentials, 'token_uri', None),
            'client_id': getattr(credentials, 'client_id', None),
            'client_secret': getattr(credentials, 'client_secret', None),
            'scopes': list(getattr(credentials, 'scopes', []) or []),
        }

        return Response({
            'success': True,
            'message': 'Google sign-in successful',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
            }
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'success': False, 'message': f'Error completing Google OAuth: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VideosViewSet(viewsets.ModelViewSet):
    queryset = Videos.objects.filter(is_active=True)
    serializer_class = VideosSerializer
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    
    def get_permissions(self):
        """
        Anyone can GET (view videos)
        Only authenticated users can POST (create)
        Only superusers can PATCH and DELETE (update/delete)
        """
        if self.action in ['list', 'retrieve', 'stream_video']:
            # Anyone can view and stream videos
            permission_classes = [permissions.AllowAny]
        elif self.action == 'create':
            # Only authenticated users can create
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Only superusers can update or delete
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Return videos for authenticated users or all active videos; superusers see all."""
        user = self.request.user
        qs = Videos.objects.filter(is_active=True).order_by('-uploaded_at')
        
        # If not authenticated, return all active videos (public access)
        if not user.is_authenticated:
            return qs
        
        # Superusers see everything
        if user.is_superuser:
            return qs
        
        # Regular authenticated users see only their videos
        return qs.filter(created_by=user)
    
    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user if self.request.user.is_authenticated else None
        )
    
    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user if self.request.user.is_authenticated else None
        )
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete video - only superusers can access this"""
        instance = self.get_object()
        instance.is_active = False
        instance.deleted = True
        instance.save()
        return Response({'success': True, 'message': 'Video deleted successfully'}, status=status.HTTP_200_OK)
    

class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    
    def get_queryset(self):
        user = self.request.user
        qs = Session.objects.filter(is_active=True).order_by('-updated_at')
        if not user.is_authenticated:
            return qs.filter(user__isnull=True)
        if user.is_superuser:
            return qs
        return qs.filter(user=user)
    
    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user if self.request.user.is_authenticated else None,
            created_by=self.request.user if self.request.user.is_authenticated else None
        )
    
    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user if self.request.user.is_authenticated else None
        )
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete session"""
        instance = self.get_object()
        instance.is_active = False
        instance.deleted = True
        instance.save()
        return Response({'success': True, 'message': 'Session deleted successfully'}, status=status.HTTP_200_OK)


class ChatWindowViewSet(viewsets.ModelViewSet):
    queryset = ChatWindow.objects.filter(is_active=True)
    serializer_class = ChatWindowSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination
    http_method_names = ['get', 'post', 'head', 'options']
    
    def get_queryset(self):        
        user = self.request.user
        qs = ChatWindow.objects.filter(is_active=True)
        if not user.is_authenticated:
            return ChatWindow.objects.none()
        if user.is_superuser:
            return qs
        return qs.filter(Q(session__user=user) | Q(session__created_by=user))
    
    def create(self, request, *args, **kwargs):
        try:
            # Validate required fields
            session_id = request.data.get('session')
            prompt = request.data.get('prompt')
            url = request.data.get('url')
            
            if not prompt:
                return Response(
                    {'success': False, 'error': 'Prompt is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not url:
                return Response(
                    {'success': False, 'error': 'URL is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Normalize URL and detect type
            url = normalize_url(url)
            url_type, identifier = detect_url_type(url)
            
            # Handle session: use provided session, find last active session, or create new one
            session = None
            
            if session_id:
                # User provided a session ID - try to use it
                try:
                    session = Session.objects.get(id=session_id, is_active=True)
                except Session.DoesNotExist:
                    return Response(
                        {'success': False, 'error': 'Session not found or inactive'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # No session ID provided - auto-create or reuse last active session
                if request.user.is_authenticated:
                    # For authenticated users, try to get their most recent active session
                    session = Session.objects.filter(
                        user=request.user, 
                        is_active=True
                    ).order_by('-created_at').first()
                else:
                    pass
                
                # If no active session found, create a new one
                if not session:
                    session = Session.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        name=f"Chat Session - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                        created_by=request.user if request.user.is_authenticated else None
                    )
            
            # Create ChatWindow instance
            chat_window_obj = ChatWindow.objects.create(
                session=session,
                prompt=prompt,
                url=url
            )
            
            # Route to appropriate agent based on URL type
            if url_type == 'app':
                # Google Play Store app - use app reviews agent
                try:
                    # Get max_reviews from request or default to 500
                    max_reviews = request.data.get('max_reviews', 500)
                    if not isinstance(max_reviews, int) or max_reviews < 1:
                        max_reviews = 500
                    max_reviews = min(max_reviews, 1000)  # Cap at 1000
                    
                    # Create output directory in media/agent for temporary chart generation
                    output_dir = Path(settings.MEDIA_ROOT) / 'agent' / f'app_analysis_{chat_window_obj.id}'
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Run app analysis
                    result = analyze_app_and_report(
                        app_name=identifier,
                        max_reviews=max_reviews,
                        output_dir=str(output_dir)
                    )
                    
                    if not result.get('success'):
                        error_msg = result.get('error', 'Unknown error during app analysis')
                        chat_window_obj.response = f"Error during analysis: {error_msg}"
                        chat_window_obj.save()
                        return Response(
                            {'success': False, 'error': error_msg}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                    
                    # Store structured analysis data in database (JSON field)
                    analysis_data = result.get('analysis_data', {})
                    chat_window_obj.analysis_data = analysis_data
                    
                    # Generate a human-readable summary for the response field
                    sentiment = analysis_data.get('sentiment_summary', {})
                    reviews_count = result.get('reviews_analyzed', 0)
                    
                    response_summary = f"""
                                        
                                        App Analysis Complete
                                        App: {identifier}
                                        Reviews Analyzed: {reviews_count}

                                        Sentiment Overview:
                                        - Positive: {sentiment.get('positive_count', 0)} ({sentiment.get('positive_percentage', 0):.1f}%)
                                        - Negative: {sentiment.get('negative_count', 0)} ({sentiment.get('negative_percentage', 0):.1f}%)
                                        - Neutral: {sentiment.get('neutral_count', 0)} ({sentiment.get('neutral_percentage', 0):.1f}%)

                                        Executive Summary:
                                        {analysis_data.get('executive_summary', 'Analysis completed successfully.')}

                                        See charts and detailed analysis in the structured data.
                                    """
                    
                    chat_window_obj.response = response_summary
                    chat_window_obj.save()
                    
                    # Save chart images to ScreenshotImage model
                    chart_paths = result.get('chart_paths', {})
                    for idx, (chart_name, chart_path) in enumerate(chart_paths.items(), start=1):
                        chart_file = Path(chart_path)
                        if chart_file.exists():
                            with open(chart_file, 'rb') as img_file:
                                image_content = ContentFile(img_file.read())
                                screenshot_img = ScreenshotImage.objects.create(
                                    chat_window=chat_window_obj,
                                    image_order=idx
                                )
                                screenshot_img.image.save(
                                    f'chart_{chat_window_obj.id}_{chart_name}.png',
                                    image_content,
                                    save=True
                                )
                    
                    # Clean up temporary JSON/text files (keep only images in database)
                    for file_to_remove in ['analysis_report.md', 'analysis_data.json', 'raw_analysis.txt']:
                        file_path = output_dir / file_to_remove
                        if file_path.exists():
                            file_path.unlink()
                    
                    # Serialize and return response
                    serializer = self.get_serializer(chat_window_obj)
                    return Response(
                        {
                            'success': True,
                            'message': 'App analysis completed successfully',
                            'data': serializer.data,
                            'session_id': session.id,
                            'session_name': session.name,
                            'is_new_session': session_id is None,
                            'analysis_type': 'app',
                            'app_id': identifier,
                            'reviews_analyzed': reviews_count,
                            'charts_saved': len(chart_paths)
                        }, 
                        status=status.HTTP_201_CREATED
                    )
                    
                except Exception as agent_error:
                    import traceback
                    error_detail = traceback.format_exc()
                    chat_window_obj.response = f"Error during app analysis: {str(agent_error)}"
                    chat_window_obj.save()
                    return Response(
                        {'success': False, 'error': f'App analysis agent failed: {str(agent_error)}'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            else:
                # Regular website - use browser screenshot agent
                try:
                    # n=2 means take maximum 2 screenshots
                    image_paths, analysis_report = asyncio.run(
                        screenshot_agent(prompt=prompt, url=url, n=2)
                    )
                    
                    # Save analysis report to ChatWindow
                    chat_window_obj.response = analysis_report
                    chat_window_obj.save()
                    
                    # Save screenshot images
                    for idx, image_path in enumerate(image_paths):
                        with open(image_path, 'rb') as img_file:
                            image_content = ContentFile(img_file.read())
                            screenshot_img = ScreenshotImage.objects.create(
                                chat_window=chat_window_obj,
                                image_order=idx + 1
                            )
                            screenshot_img.image.save(
                                f'screenshot_{chat_window_obj.id}_{idx+1}.png',
                                image_content,
                                save=True
                            )
                    
                    # Serialize and return response
                    serializer = self.get_serializer(chat_window_obj)
                    return Response(
                        {
                            'success': True,
                            'message': 'Website analysis completed successfully',
                            'data': serializer.data,
                            'session_id': session.id,
                            'session_name': session.name,
                            'is_new_session': session_id is None,
                            'analysis_type': 'website'
                        }, 
                        status=status.HTTP_201_CREATED
                    )
                    
                except Exception as agent_error:
                    chat_window_obj.response = f"Error during analysis: {str(agent_error)}"
                    chat_window_obj.save()
                    return Response(
                        {'success': False, 'error': f'Screenshot agent failed: {str(agent_error)}'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
        
        except Exception as e:
            return Response(
                {'success': False, 'error': f'Unexpected error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED) 


from agent.ai_mgt import image_analysis_manager, recommendation_agent_manager, writer_agent_manager, run_full_analysis_pipeline

class DeepChatViewSet(viewsets.ModelViewSet):
    queryset = DeepChat.objects.filter(is_active=True)
    serializer_class = DeepChatSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination
    http_method_names = ['get', 'post', 'head', 'options']
    
    def get_queryset(self):        
        user = self.request.user
        qs = DeepChat.objects.filter(is_active=True).order_by('-created_at')
        if not user.is_authenticated:
            return DeepChat.objects.none()
        if user.is_superuser:
            return qs
        return qs.filter(Q(session__user=user) | Q(session__created_by=user))
    
    def create(self, request, *args, **kwargs):
        """
        Create a new DeepChat analysis for a given URL.
        
        Request body:
        - prompt (required): User's analysis request/persona description
        - url (required): URL of the website to analyze
        - session (optional): Session ID to associate with this chat
        - max_screenshots (optional): Maximum screenshots to capture (default: 3, max: 6)
        - additional_context (optional): Additional business context for analysis
        
        Response:
        - success: Boolean indicating success
        - data: DeepChat object with analysis_data containing structured JSON report
        - session_id: Associated session ID
        - cto_analysis: Raw CTO technical analysis
        - pm_analysis: Raw Project Manager analysis
        """
        try:
            # Extract and validate request data
            session_id = request.data.get('session', None)
            prompt = request.data.get('prompt', '')
            url = request.data.get('url', '')
            max_screenshots = request.data.get('max_screenshots', 3)
            additional_context = request.data.get('additional_context', None)

            # Validate required fields
            if not prompt:
                return Response(
                    {'success': False, 'error': 'Prompt is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                ) 
            
            if not url:
                return Response(
                    {'success': False, 'error': 'URL is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate max_screenshots
            try:
                max_screenshots = int(max_screenshots)
                max_screenshots = min(max(max_screenshots, 1), 6)  # Clamp between 1 and 6
            except (ValueError, TypeError):
                max_screenshots = 3

            # Normalize URL
            url = normalize_url(url)
            
            # Handle session: use provided, find existing, or create new
            session = None
            if session_id:
                try:
                    session = Session.objects.get(id=session_id, is_active=True)
                    # Verify ownership
                    if request.user.is_authenticated and not request.user.is_superuser:
                        if session.user != request.user and session.created_by != request.user:
                            return Response(
                                {'success': False, 'error': 'Session not found or access denied'}, 
                                status=status.HTTP_404_NOT_FOUND
                            )
                except Session.DoesNotExist:
                    return Response(
                        {'success': False, 'error': 'Session not found or inactive'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Auto-create or reuse last active session
                if request.user.is_authenticated:
                    session = Session.objects.filter(
                        user=request.user, 
                        is_active=True
                    ).order_by('-created_at').first()
                
                if not session:
                    session = Session.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        name=f"Deep Analysis - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                        created_by=request.user if request.user.is_authenticated else None
                    )

            # Create DeepChat instance
            deep_chat_obj = DeepChat.objects.create(
                session=session,
                prompt=prompt,
                url=url
            )

            try:
                # Step 1: Capture screenshots using browser agent
                image_paths, _ = asyncio.run(
                    screenshot_agent(prompt=prompt, url=url, n=max_screenshots)
                )
                
                if not image_paths:
                    deep_chat_obj.analysis_data = {
                        'error': 'Failed to capture screenshots',
                        'success': False
                    }
                    deep_chat_obj.save()
                    return Response(
                        {'success': False, 'error': 'Failed to capture screenshots from URL'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                # Convert image paths to Path objects
                image_path_objects = [Path(img_path) for img_path in image_paths]
                
                # Step 2: Run CTO-level image analysis
                cto_analysis = image_analysis_manager(
                    image_paths=image_path_objects,
                    page_url=url,
                    persona_note=prompt,
                    image_model="gemini-2.5-flash-image",
                    max_images_for_model=max_screenshots,
                    max_tokens=16000,
                    temperature=0.2
                )
                
                # Step 3: Run Project Manager analysis
                pm_analysis = recommendation_agent_manager(
                    analysis=cto_analysis,
                    additional_context=additional_context,
                    model_name="gpt-4o-mini",
                    max_tokens=12000,
                    temperature=0.1
                )
                
                # Step 4: Generate structured JSON report
                final_report = writer_agent_manager(
                    cto_analysis=cto_analysis,
                    pm_analysis=pm_analysis,
                    model_name="gpt-4o-mini",
                    max_tokens=16000,
                    temperature=0.0
                )
                
                # Add metadata to the report
                if isinstance(final_report, dict):
                    final_report['_metadata'] = {
                        'url_analyzed': url,
                        'persona_prompt': prompt,
                        'screenshots_captured': len(image_paths),
                        'analysis_timestamp': timezone.now().isoformat(),
                        'deep_chat_id': deep_chat_obj.id,
                        'session_id': session.id
                    }
                    final_report['_raw_analyses'] = {
                        'cto_analysis': cto_analysis,
                        'pm_analysis': pm_analysis
                    }
                
                # Save analysis data to DeepChat
                deep_chat_obj.analysis_data = final_report
                deep_chat_obj.save()
                
                # Save screenshot images to ScreenshotImage model
                saved_screenshots = []
                for idx, img_path in enumerate(image_paths):
                    try:
                        img_path_obj = Path(img_path)
                        if img_path_obj.exists():
                            with open(img_path, 'rb') as img_file:
                                image_content = ContentFile(img_file.read())
                                screenshot_img = ScreenshotImage.objects.create(
                                    deep_chat=deep_chat_obj,
                                    image_order=idx + 1
                                )
                                screenshot_img.image.save(
                                    f'deep_chat_{deep_chat_obj.id}_screenshot_{idx + 1}.png',
                                    image_content,
                                    save=True
                                )
                                saved_screenshots.append(screenshot_img.id)
                    except Exception as img_error:
                        # Log but don't fail the entire request if image save fails
                        print(f"Error saving screenshot {idx + 1}: {str(img_error)}")
                
                # Refresh the deep_chat_obj from database to include screenshots
                deep_chat_obj.refresh_from_db()
                
                # Serialize and return response
                serializer = self.get_serializer(deep_chat_obj)
                
                # Get saved screenshots count
                saved_screenshots_count = ScreenshotImage.objects.filter(deep_chat=deep_chat_obj).count()
                
                return Response(
                    {
                        'success': True,
                        'message': 'Deep analysis completed successfully',
                        'data': serializer.data,
                        'session_id': session.id,
                        'session_name': session.name,
                        'is_new_session': session_id is None,
                        'screenshots_captured': len(image_paths),
                        'screenshots_saved': saved_screenshots_count,
                        'analysis_type': 'deep_chat',
                        'url_analyzed': url
                    }, 
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as agent_error:
                error_detail = traceback.format_exc()
                deep_chat_obj.analysis_data = {
                    'error': str(agent_error),
                    'error_detail': error_detail,
                    'success': False
                }
                deep_chat_obj.save()
                return Response(
                    {'success': False, 'error': f'Analysis agent failed: {str(agent_error)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Exception as e:
            return Response(
                {'success': False, 'error': f'Unexpected error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


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
    http_method_names = ['get', 'head', 'options']
    
    def create(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def perform_update(self, serializer):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


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
    
        return super().perform_create(serializer)
    
    def update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class EmailSubscribeViewSet(viewsets.ModelViewSet):
    queryset = EmailSubscribe.objects.all()
    serializer_class = EmailSubscribeSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination

    def perform_create(self, serializer):
        serializer.save(user=self.request.user if self.request.user.is_authenticated else None)        
        return super().perform_create(serializer)

    def update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class WaitListViewSet(viewsets.ModelViewSet):
    queryset = WaitList.objects.filter(is_active=True)
    serializer_class = WaitListSerializer
    permission_classes = [permissions.AllowAny] 
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication] 
    pagination_class = DynamicPagination 

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user if self.request.user.is_authenticated else None
        )
        return super().perform_create(serializer) 
    
    def update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    

class BlogCategoryViewSet(viewsets.ModelViewSet):
    queryset = BlogCategory.objects.filter(is_active=True)
    serializer_class = BlogCategorySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination
    http_method_names = ['get', 'head', 'options'] 


    def create(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class BlogPostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.filter(is_active=True)
    serializer_class = BlogPostSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination
    http_method_names = ['get', 'head', 'options'] 

    def create(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    
class BookCalendarViewSet(viewsets.ModelViewSet):
    queryset = BookCalendar.objects.all()
    serializer_class = BookCalendarSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination 
    
    def get_queryset(self):
        """Return bookings only for the authenticated user"""
        if self.request.user.is_authenticated:
            return BookCalendar.objects.filter(user=self.request.user).order_by('-created_at')
        return BookCalendar.objects.none()
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = serializer.validated_data

            # Service account credentials (no user OAuth / no Google Meet for now)
            SERVICE_ACCOUNT_FILE = os.path.join(settings.BASE_DIR, 'credentials.json')
            SCOPES = ['https://www.googleapis.com/auth/calendar']
            CALENDAR_ID = "iht2889@gmail.com"

            try:
                credentials = ServiceAccountCredentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            except Exception as cred_err:
                return Response({'success': False, 'message': f'Credential load error: {cred_err}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            service = build('calendar', 'v3', credentials=credentials)

            tz = data.get('timezone', 'UTC')
            tzinfo = pytz.timezone(tz)
            start_dt = data.get('start_datetime')
            end_dt = data.get('end_datetime')

            if not start_dt:
                return Response({'success': False, 'message': 'start_datetime is required.'}, status=status.HTTP_400_BAD_REQUEST)
            if not end_dt:
                end_dt = start_dt + timedelta(hours=1)

            start_dt = (tzinfo.localize(start_dt) if start_dt.tzinfo is None else start_dt.astimezone(tzinfo))
            end_dt = (tzinfo.localize(end_dt) if end_dt.tzinfo is None else end_dt.astimezone(tzinfo))

            if start_dt >= end_dt:
                end_dt = start_dt + timedelta(hours=1)

            summary = data.get('summary')
            description = data.get('description', '')
            location = data.get('location', '')
            if not summary:
                return Response({'success': False, 'message': 'summary is required.'}, status=status.HTTP_400_BAD_REQUEST)

            # Optional colorId from raw request (not necessarily in serializer)
            color_id = request.data.get('colorId')

            # Attendees parsing
            attendees_raw = data.get('attendees')
            attendees_list = []
            if isinstance(attendees_raw, list):
                attendees_list = [e.strip() for e in attendees_raw if isinstance(e, str) and e.strip()]
            elif isinstance(attendees_raw, str):
                attendees_list = [e.strip() for e in attendees_raw.split(',') if e.strip()]

            event = {
                'summary': summary,
                'description': description,
                'location': location or None,
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': tz,
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': tz,
                },
            }
            
            if color_id:
                event['colorId'] = str(color_id)
            if attendees_list:
                event['attendees'] = []

            if data.get('reminders', False):
                event['reminders'] = {
                    'useDefault': False,
                    'overrides': [
                       
                    ],
                }

            created_event = service.events().insert(
                calendarId=CALENDAR_ID,
                body=event, 
                conferenceDataVersion=1 
            ).execute()

            book_link = created_event.get('htmlLink')

            calendar_fields = {f.name for f in BookCalendar._meta.get_fields() if getattr(f, 'concrete', False) and not f.many_to_many}
            booking_kwargs = {
                'user': request.user if request.user.is_authenticated else None,
                'summary': summary,
                'description': description,
                'location': location,
                'book_link': book_link,
                'meet_link': '', 
                'timezone': tz,
                'start_datetime': start_dt.astimezone(pytz.UTC),
                'end_datetime': end_dt.astimezone(pytz.UTC),
                'reminders': data.get('reminders', False),
            }
            for extra_key in ['full_name', 'email', 'phone_number']:
                if extra_key in data and extra_key in calendar_fields:
                    booking_kwargs[extra_key] = data.get(extra_key)
            if 'attendees' in calendar_fields and attendees_list:
                booking_kwargs['attendees'] = ','.join(attendees_list)

            booking = BookCalendar.objects.create(**{k: v for k, v in booking_kwargs.items() if k in calendar_fields})
            response_serializer = self.get_serializer(booking)

            return Response({
                'success': True,
                'data': response_serializer.data,
                'message': 'Calendar event created successfully (service account)'
            }, status=status.HTTP_201_CREATED)

        except HttpError as error:
            return Response({'success': False, 'message': f'Google Calendar API error: {error}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'success': False, 'message': f'Error creating calendar event: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    
    def update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)



class TermsAndConditionsViewSet(viewsets.ModelViewSet):
    queryset = TermsAndConditions.objects.filter(is_active=True)
    serializer_class = TermsAndConditionsSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination
    http_method_names = ['get', 'head', 'options'] 

    def create(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    
    
class PrivacyPolicyViewSet(viewsets.ModelViewSet):
    queryset = PrivacyPolicy.objects.filter(is_active=True)
    serializer_class = PrivacyPolicySerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = [CsrfExemptSessionAuthentication, JWTAuthentication]
    pagination_class = DynamicPagination
    http_method_names = ['get', 'head', 'options'] 

    def create(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    def update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    def partial_update(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    def destroy(self, request, *args, **kwargs):
        return Response({'message': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


