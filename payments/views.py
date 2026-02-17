# payments/views.py

from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
import stripe
from django.conf import settings

from .models import Wallet, WalletTransaction, Purchase, Payment
from .serializers import (
    WalletSerializer, 
    WalletTransactionSerializer, 
    PurchaseSerializer,
    PaymentSerializer,
    AddFundsSerializer,
    PurchasePostSerializer
)
from posts.models import Post

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_balance(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    serializer = WalletSerializer(wallet)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_add_funds_intent(request):
    serializer = AddFundsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    amount = Decimal(str(serializer.validated_data['amount']))

    try:
        amount_cents = int(amount * 100)

        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='usd',
            metadata={
                'user_id': request.user.id,
                'username': request.user.username,
                'type': 'add_funds'
            },
            description=f'Add ${amount} to wallet for {request.user.username}'
        )

        return Response({
            'client_secret': payment_intent.client_secret,
            'payment_intent_id': payment_intent.id,
            'amount': float(amount)
        })
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_intent(request):
    serializer = PurchasePostSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    post_id = serializer.validated_data['post_id']
    post = get_object_or_404(Post, id=post_id)

    if not post.is_exclusive:
        return Response({'error': 'This post is not exclusive content'}, status=status.HTTP_400_BAD_REQUEST)
    if Purchase.objects.filter(user=request.user, post=post).exists():
        return Response({'error': 'You have already purchased this content'}, status=status.HTTP_400_BAD_REQUEST)
    if post.author == request.user:
        return Response({'error': 'You cannot purchase your own content'}, status=status.HTTP_400_BAD_REQUEST)

    amount = Decimal(str(post.price)) if post.price else Decimal('4.99')

    try:
        amount_cents = int(amount * 100)
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='usd',
            metadata={
                'user_id': request.user.id,
                'username': request.user.username,
                'post_id': post.id,
                'type': 'purchase_content'
            },
            description=f'Purchase exclusive content from @{post.author.username}'
        )
        return Response({
            'client_secret': payment_intent.client_secret,
            'payment_intent_id': payment_intent.id,
            'amount': float(amount)
        })
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_payment(request):
    payment_intent_id = request.data.get('payment_intent_id')
    post_id = request.data.get('post_id')

    if not payment_intent_id:
        return Response({'error': 'Payment intent ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        if payment_intent.status != 'succeeded':
            return Response({'error': f'Payment status: {payment_intent.status}'}, status=status.HTTP_400_BAD_REQUEST)

        amount = Decimal(payment_intent.amount) / Decimal(100)

        with transaction.atomic():
            wallet, _ = Wallet.objects.get_or_create(user=request.user)

            if post_id:
                post = get_object_or_404(Post, id=post_id)
                if Purchase.objects.filter(user=request.user, post=post).exists():
                    return Response({'error': 'Already purchased'}, status=status.HTTP_400_BAD_REQUEST)

                purchase = Purchase.objects.create(
                    user=request.user,
                    post=post,
                    amount=amount,
                    stripe_payment_intent_id=payment_intent_id
                )

                Payment.objects.create(
                    user=request.user,
                    amount=amount,
                    stripe_payment_id=payment_intent_id,
                    status='completed',
                    description=f'Purchase: Exclusive Post #{post.id}'
                )

                return Response({
                    'success': True,
                    'message': 'Content unlocked successfully!',
                    'purchase_id': purchase.id,
                    'wallet_balance': float(wallet.balance)
                })
            else:
                # Add funds to wallet safely
                wallet.add_funds(
                    amount=amount,
                    description='Funds Added via Stripe',
                    payment_intent_id=payment_intent_id
                )

                Payment.objects.create(
                    user=request.user,
                    amount=amount,
                    stripe_payment_id=payment_intent_id,
                    status='completed',
                    description='Add Funds to Wallet'
                )

                return Response({
                    'success': True,
                    'message': 'Funds added successfully!',
                    'new_balance': float(wallet.balance)
                })

    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_purchase_history(request):
    purchases = Purchase.objects.filter(user=request.user).select_related('post', 'post__author')
    serializer = PurchaseSerializer(purchases, many=True)
    return Response({'results': serializer.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_transactions(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all()
    serializer = WalletTransactionSerializer(transactions, many=True)
    return Response({'results': serializer.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_post_access(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if not post.is_exclusive:
        return Response({'has_access': True, 'reason': 'not_exclusive'})
    if post.author == request.user:
        return Response({'has_access': True, 'reason': 'owner'})
    has_purchased = Purchase.objects.filter(user=request.user, post=post).exists()
    if has_purchased:
        return Response({'has_access': True, 'reason': 'purchased'})
    else:
        return Response({
            'has_access': False,
            'price': float(post.price) if post.price else 4.99
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_history(request):
    payments = Payment.objects.filter(user=request.user)
    serializer = PaymentSerializer(payments, many=True)
    return Response({'results': serializer.data})
