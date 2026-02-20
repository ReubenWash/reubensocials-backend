from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Follow

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    is_following = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'bio', 'profile_picture', 'cover_photo', 'is_creator',
                  'followers_count', 'following_count', 'posts_count', 'website',
                  'twitter', 'instagram', 'created_at', 'is_following']
        read_only_fields = ['id', 'created_at']

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(follower=request.user, following=obj).exists()
        return False

    def get_posts_count(self, obj):
        """Get total posts count for this user"""
        return obj.posts.count()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration with profile picture"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    profile_picture = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm',
                  'first_name', 'last_name', 'profile_picture']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        profile_picture = validated_data.pop('profile_picture', None)

        user = User.objects.create_user(**validated_data)

        if profile_picture:
            user.profile_picture = profile_picture
            user.save()

        return user


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for profile updates"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'bio', 'profile_picture',
                  'cover_photo', 'website', 'twitter', 'instagram']

    def validate_bio(self, value):
        if len(value) > 500:
            raise serializers.ValidationError("Bio cannot exceed 500 characters.")
        return value


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer to allow login with EMAIL instead of username.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = serializers.EmailField()
        self.fields['username'].required = False

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError('Email and password are required.')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('No account found with this email address.')

        if not user.check_password(password):
            raise serializers.ValidationError('Incorrect password.')

        if not user.is_active:
            raise serializers.ValidationError('This account is inactive.')

        # Inject username so parent validate() works
        attrs['username'] = user.username
        return super().validate(attrs)