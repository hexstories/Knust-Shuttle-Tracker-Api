from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .serializers import *
from .models import User, User_Profile
import os
import requests
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.authentication import TokenAuthentication,SessionAuthentication
from rest_framework import generics, status
from django.contrib.auth import authenticate, login, logout
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
"""from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
CALLBACK_URL_YOU_SET_ON_GOOGLE = os.environ.get('CALLBACK_URL_YOU_SET_ON_GOOGLE')"""

"""class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = CALLBACK_URL_YOU_SET_ON_GOOGLE
    client_class = OAuth2Client"""

@api_view(["GET"])
def get_user_token(request):
    user = request.user

    # Check if a token already exists for the user
    token, created = Token.objects.get_or_create(user=user)
    key = token.key
    user = token.user.username
    return Response({'key':key,"user":user})

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]  # Allow anyone to register

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(username=request.data['username'])
            token, _ = Token.objects.get_or_create(user=user)
            response.data['token'] = token.key
        return response

class UserOtpVerification(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserOtpVerificationSerializer
    
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data.get('code')
        user_id = serializer.validated_data.get('user_id')
        phone = serializer.validated_data.get('phone')
        data = {
            "code": code,
            "number": phone,
        }

        headers = {
        'api-key': os.environ.get('ARK_API_KEY'),
        }

        url = 'https://sms.arkesel.com/api/otp/verify'

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200 and response.json().get("message") == "Successful":
            print(response.json())
            user = User.objects.get(pk=user_id)
            user.is_active = True
            user.save()
            return Response({"message": "User is verified"}, status=200)
        elif response.status_code == 200 and response.json().get("message") == "Code has expired":
            return Response({"message": "Code has expired"}, status=400)
        elif response.status_code == 200 and response.json().get("message") == "Invalid code":
            return Response({"message": "Code incorrect"}, status=400)
        else:
            print(f"Error: {response.status_code} and {response.json()}")
            return Response({"message": "Code incorrect"}, status=400)
       
class UserLoginView(generics.CreateAPIView):
    serializer_class = UserLoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise AuthenticationFailed(detail="Invalid username")

        user = authenticate(username=username, password=password)
        if user is None:
            raise AuthenticationFailed(detail="Invalid password")

        token, _ = Token.objects.get_or_create(user=user)

        # Log the user in within the session
        login(request, user)

        return Response({"message": "Login successful", "token": token.key}, status=status.HTTP_200_OK)

class UserLogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication,SessionAuthentication]
    def get(self, request, *args, **kwargs):
        logout(request)
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

class UserUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class UserProfileUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    serializer_class = UserProfileSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_object(self):
        return User_Profile.objects.get(user=self.request.user)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class UserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication,SessionAuthentication]
    serializer_class = FullUserSerializer
    def get_queryset(self):
        return User.objects.filter(pk=self.request.user.id)

class UserResendOTP(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserResendOtpSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone = serializer.validated_data.get('phone')
        user_id = serializer.validated_data.get('user_id')
        user = User.objects.get(pk=user_id)
        message = f"Hello {user.username}, Welcome to Dreamosoft."
        data = {
        'expiry': 5,
        'length': 6,
        'medium': 'sms',
        'message': message+' This is your verification code:\n%otp_code%\nPlease do not share this code with anyone.',
        'number': phone,
        'sender_id': 'Drmosft',
        'type': 'numeric',
        }

        headers = {
        'api-key': os.environ.get('ARK_API_KEY'),
        }

        url = 'https://sms.arkesel.com/api/otp/generate'

        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200 and response.json().get("message") == "Successful, OTP is being processed for delivery.":
            return Response({"message": "OTP sent"}, status=200)
        else:
            return Response({"message": "OTP not sent","Error": response.status_code, "Api_error":response.json()}, status=400)
