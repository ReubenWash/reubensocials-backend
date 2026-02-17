# payments/models.py

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class Payment(models.Model):
    """Payment transactions"""
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_payment_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - ${self.amount} - {self.status}"


class Wallet(models.Model):
    """User wallet for storing balance"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Wallet'
        verbose_name_plural = 'Wallets'

    def __str__(self):
        return f"{self.user.username}'s Wallet - ${self.balance}"

    def add_funds(self, amount, description="Funds Added", payment_intent_id=None):
        """Add funds to wallet"""
        self.balance += amount
        self.save()
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='credit',
            amount=amount,
            description=description,
            stripe_payment_intent_id=payment_intent_id
        )

    def deduct_funds(self, amount, description="Purchase", payment_intent_id=None):
        """Deduct funds from wallet"""
        if self.balance < amount:
            raise ValueError("Insufficient balance")
        
        self.balance -= amount
        self.save()
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=self,
            transaction_type='debit',
            amount=amount,
            description=description,
            stripe_payment_intent_id=payment_intent_id
        )


class WalletTransaction(models.Model):
    """Wallet transaction history"""
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]
    
    wallet = models.ForeignKey(
        Wallet, 
        on_delete=models.CASCADE, 
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=10, 
        choices=TRANSACTION_TYPES
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    stripe_payment_intent_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'

    def __str__(self):
        return f"{self.transaction_type.upper()} - ${self.amount} - {self.wallet.user.username}"


class Purchase(models.Model):
    """Track purchases of exclusive content"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='content_purchases'  # Changed from 'purchases'
    )
    post = models.ForeignKey(
        'posts.Post', 
        on_delete=models.CASCADE, 
        related_name='user_purchases'  # Changed from 'purchases'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_payment_intent_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'post']
        ordering = ['-created_at']
        verbose_name = 'Purchase'
        verbose_name_plural = 'Purchases'

    def __str__(self):
        return f"{self.user.username} - Post #{self.post.id} - ${self.amount}"