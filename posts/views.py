from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Post, Like, Comment, PostPurchase
from .serializers import PostSerializer, CommentSerializer
from notifications.models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import cloudinary
import cloudinary.utils


# -------------------------
# POSTS
# -------------------------
class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        following_users = user.following.values_list('following', flat=True)
        return Post.objects.filter(
            Q(author=user) | Q(author__in=following_users)
        ).select_related('author').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()
        post.views_count += 1
        post.save()
        serializer = self.get_serializer(post)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class TrendingPostsView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        week_ago = timezone.now() - timedelta(days=7)
        return Post.objects.filter(
            created_at__gte=week_ago,
            is_exclusive=False
        ).order_by('-likes_count', '-views_count')[:20]


class UserPostsView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        username = self.kwargs['username']
        return Post.objects.filter(author__username=username).order_by('-created_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_post(request, pk):
    try:
        post = Post.objects.get(pk=pk)
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        post.likes_count -= 1
        post.save()
        return Response({'message': 'Unliked', 'is_liked': False})
    else:
        post.likes_count += 1
        post.save()
        if post.author != request.user:
            notification = Notification.objects.create(
                recipient=post.author,
                sender=request.user,
                notification_type='like',
                content=f"{request.user.username} liked your post",
                link=f"/post/{post.id}"
            )
            from notifications.serializers import NotificationSerializer
            notif_data = NotificationSerializer(notification).data
            send_realtime_notification(post.author.id, notif_data)
        return Response({'message': 'Liked', 'is_liked': True}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_post(request, pk):
    try:
        post = Post.objects.get(pk=pk)
        post.shares_count += 1
        post.save()
        return Response({'message': 'Post shared', 'shares_count': post.shares_count})
    except Post.DoesNotExist:
        return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)


# -------------------------
# COMMENTS
# -------------------------
class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        post_id = self.kwargs['post_id']
        return Comment.objects.filter(post_id=post_id).select_related('user').order_by('-created_at')

    def create(self, request, *args, **kwargs):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, pk=post_id)

        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Content required'}, status=status.HTTP_400_BAD_REQUEST)

        comment = Comment.objects.create(user=request.user, post=post, content=content)
        post.comments_count += 1
        post.save()

        if post.author != request.user:
            notification = Notification.objects.create(
                recipient=post.author,
                sender=request.user,
                notification_type='comment',
                content=f"{request.user.username} commented on your post",
                link=f"/post/{post.id}"
            )
            from notifications.serializers import NotificationSerializer
            notif_data = NotificationSerializer(notification).data
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'notifications_{post.author.id}',
                {'type': 'send_notification', 'notification': notif_data}
            )

        serializer = self.get_serializer(comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def explore_posts(request):
    posts = Post.objects.filter(is_exclusive=False).order_by('-likes_count', '?')[:30]
    serializer = PostSerializer(posts, many=True, context={'request': request})
    return Response(serializer.data)


# -------------------------
# SECURE EXCLUSIVE MEDIA
# -------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_exclusive_video(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if not post.is_exclusive:
        return Response({'error': 'This post is not exclusive'}, status=400)

    purchased = PostPurchase.objects.filter(user=request.user, post=post).exists()
    if post.author != request.user and not purchased:
        return Response({'error': 'You are not authorized to view this video'}, status=403)

    video_url = cloudinary.utils.cloudinary_url(
        post.video.public_id,
        resource_type='video',
        type='authenticated',
        sign_url=True,
        format='mp4',
        secure=True
    )[0]

    return Response({'video_url': video_url})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_exclusive_image(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if not post.is_exclusive:
        return Response({'error': 'This post is not exclusive'}, status=400)

    purchased = PostPurchase.objects.filter(user=request.user, post=post).exists()
    if post.author != request.user and not purchased:
        return Response({'error': 'You are not authorized to view this image'}, status=403)

    image_url = cloudinary.utils.cloudinary_url(
        post.image.public_id,
        type='authenticated',
        sign_url=True,
        secure=True
    )[0]

    return Response({'image_url': image_url})


# -------------------------
# REAL-TIME NOTIFICATIONS
# -------------------------
def send_realtime_notification(user_id, notification_data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user_id}',
        {'type': 'send_notification', 'notification': notification_data}
    )