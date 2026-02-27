from rest_framework import serializers
from .models import Post, Like, Comment, PostPurchase
from accounts.serializers import UserSerializer

class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_purchased = serializers.SerializerMethodField()
    can_view = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'author', 'content', 'post_type', 'media_file',
                  'thumbnail', 'media_url', 'thumbnail_url', 'is_exclusive',
                  'price', 'likes_count', 'comments_count', 'views_count',
                  'shares_count', 'created_at', 'is_liked', 'is_purchased', 'can_view']
        read_only_fields = ['id', 'author', 'likes_count', 'comments_count',
                            'views_count', 'shares_count', 'created_at']

    def get_media_url(self, obj):
        if obj.media_file:
            return obj.media_file.url  # Cloudinary returns the full URL
        return None

    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            return obj.thumbnail.url  # Cloudinary returns the full URL
        return None

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(user=request.user, post=obj).exists()
        return False

    def get_is_purchased(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return PostPurchase.objects.filter(user=request.user, post=obj).exists()
        return False

    def get_can_view(self, obj):
        request = self.context.get('request')
        if not obj.is_exclusive:
            return True
        if request and request.user.is_authenticated:
            if obj.author == request.user:
                return True
            return self.get_is_purchased(obj)
        return False


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']