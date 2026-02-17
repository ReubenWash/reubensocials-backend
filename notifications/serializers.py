from rest_framework import serializers
from .models import Notification
from accounts.serializers import UserSerializer

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'sender', 'notification_type', 'content', 'link', 
                  'is_read', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at']