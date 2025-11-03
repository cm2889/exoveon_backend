from django.utils import timezone 
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
from rest_framework.decorators import api_view, permission_classes 
from rest_framework_simplejwt.authentication import JWTAuthentication 
from rest_framework_simplejwt.views import TokenObtainPairView 
from rest_framework_simplejwt.tokens import RefreshToken, TokenError 



from django.contrib.auth.models import User 

from backend.serializers import SignUpSerializer, SignInSerializer
from backend.models import SignLog 



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