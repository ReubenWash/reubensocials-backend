# payments/serializers.py
from decimal import Decimal
from rest_framework import serializers
from .models import Wallet, WalletTransaction, Purchase, Payment


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model"""
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Wallet
        fields = ['id', 'username', 'balance', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for Wallet Transaction"""
    username = serializers.CharField(source='wallet.user.username', read_only=True)
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 
            'username',
            'transaction_type', 
            'amount', 
            'description', 
            'stripe_payment_intent_id',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PurchaseSerializer(serializers.ModelSerializer):
    """Serializer for Purchase model"""
    post_id = serializers.IntegerField(source='post.id', read_only=True)
    post_title = serializers.CharField(source='post.content', read_only=True)
    post_thumbnail = serializers.ImageField(source='post.thumbnail', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Purchase
        fields = [
            'id', 
            'username',
            'post_id', 
            'post_title',
            'post_thumbnail',
            'amount', 
            'stripe_payment_intent_id',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'username',
            'amount',
            'stripe_payment_id',
            'status',
            'description',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']




class AddFundsSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("1.00"),
        max_value=Decimal("10000.00")
    )
    
    def validate_amount(self, value):
        """Validate amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class PurchasePostSerializer(serializers.Serializer):
    """Serializer for purchasing exclusive post"""
    post_id = serializers.IntegerField()
    
    def validate_post_id(self, value):
        """Validate post exists"""
        from posts.models import Post
        try:
            Post.objects.get(id=value)
        except Post.DoesNotExist:
            raise serializers.ValidationError("Post not found")
        return value