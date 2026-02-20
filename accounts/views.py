# accounts/views.py

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Follow
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    ProfileUpdateSerializer,
    EmailTokenObtainPairSerializer
)
from notifications.models import Notification

User = get_user_model()


# -----------------------------
# Login with Email (JWT)
# -----------------------------
class EmailTokenObtainPairView(TokenObtainPairView):
    """Login with email instead of username"""
    serializer_class = EmailTokenObtainPairSerializer


# -----------------------------
# Get currently authenticated user
# -----------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    Returns the current logged-in user details.
    """
    serializer = UserSerializer(request.user, context={'request': request})
    return Response(serializer.data)


# -----------------------------
# Register new user
# -----------------------------
class RegisterView(generics.CreateAPIView):
    """
    User registration with profile picture support.
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


# -----------------------------
# Profile view & update
# -----------------------------
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# -----------------------------
# View other users by username
# -----------------------------
class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    lookup_field = 'username'


# -----------------------------
# Search users
# -----------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return Response({'results': []})

    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id)[:20]

    serializer = UserSerializer(users, many=True, context={'request': request})
    return Response({'results': serializer.data})


# -----------------------------
# Discover users
# -----------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def discover_users(request):
    users = User.objects.exclude(id=request.user.id).order_by('-followers_count')[:50]
    serializer = UserSerializer(users, many=True, context={'request': request})
    return Response(serializer.data)


# -----------------------------
# Follow / unfollow user
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_user(request, username):
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.user == target_user:
        return Response({'error': 'Cannot follow yourself'}, status=status.HTTP_400_BAD_REQUEST)

    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=target_user
    )

    if not created:
        follow.delete()
        target_user.followers_count = max(0, target_user.followers_count - 1)
        request.user.following_count = max(0, request.user.following_count - 1)
        target_user.save()
        request.user.save()
        return Response({'message': 'Unfollowed', 'is_following': False})
    else:
        target_user.followers_count += 1
        request.user.following_count += 1
        target_user.save()
        request.user.save()

        # Create notification
        Notification.objects.create(
            recipient=target_user,
            sender=request.user,
            notification_type='follow',
            content=f"{request.user.username} started following you",
            link=f"/user/{request.user.username}"
        )

        return Response({'message': 'Followed', 'is_following': True}, status=status.HTTP_201_CREATED)


# -----------------------------
# Get followers of a user
# -----------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_followers(request, username):
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    followers = Follow.objects.filter(following=target_user).select_related('follower')
    serializer = UserSerializer([f.follower for f in followers], many=True, context={'request': request})
    return Response(serializer.data)


# -----------------------------
# Get users that a user follows
# -----------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_following(request, username):
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    following = Follow.objects.filter(follower=target_user).select_related('following')
    serializer = UserSerializer([f.following for f in following], many=True, context={'request': request})
    return Response(serializer.data)


# -----------------------------
# Logout user
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Blacklist the refresh token on logout so it can't be reused.
    Frontend must also clear tokens from localStorage.
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
    except Exception:
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)