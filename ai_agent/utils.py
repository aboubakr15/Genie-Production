from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from main.models import *

def get_credit_balance():
    """Get current project credit balance"""
    credit, created = Credits.objects.get_or_create(
        id=1,
        defaults={
            'total_credits_added': 0,
            'total_credits_used': 0
        }
    )
    return credit

def add_credits(amount, description="Credits added", user=None, expires_in_days=30):
    """Add credits to project balance with individual expiry"""
    if amount <= 0:
        raise ValidationError("Amount must be positive")
    
    with transaction.atomic():
        credit = get_credit_balance()
        credit.total_credits_added += amount
        credit.save()
        
        # Set individual expiry for this batch of credits
        expires_at = timezone.now() + timedelta(days=expires_in_days)
        
        CreditHistory.objects.create(
            transaction_type='purchase',
            amount=amount,
            description=description,
            user=user,
            expires_at=expires_at
        )
    
    return credit.get_current_balance()

def use_credits(amount, description="Feature usage", user=None, related_object=None):
    """Use credits from project balance using FIFO (oldest credits first)"""
    if amount <= 0:
        raise ValidationError("Amount must be positive")
    
    with transaction.atomic():
        # Get non-expired credits ordered by expiry (soonest first)
        available_credits = CreditHistory.objects.filter(
            transaction_type='purchase',
            expires_at__gt=timezone.now(),
            amount__gt=0
        ).order_by('expires_at', 'created_at')
        
        total_available = sum(credit.amount for credit in available_credits)
        
        if total_available < amount:
            return False  # Insufficient credits
        
        # Use credits with FIFO method
        remaining_to_use = amount
        credits_used = []
        
        for credit_batch in available_credits:
            if remaining_to_use <= 0:
                break
                
            usable_amount = min(credit_batch.amount, remaining_to_use)
            
            # Reduce the original credit batch
            credit_batch.amount -= usable_amount
            credit_batch.save()
            
            # Record the usage
            history_data = {
                'transaction_type': 'usage',
                'amount': -usable_amount,
                'description': description,
                'user': user
            }
            
            if related_object:
                if isinstance(related_object, Sheet):
                    history_data['sheet'] = related_object
                elif isinstance(related_object, SalesShow):
                    history_data['sales_show'] = related_object
            
            CreditHistory.objects.create(**history_data)
            
            remaining_to_use -= usable_amount
            credits_used.append(usable_amount)
        
        # Update total credits used
        credit = get_credit_balance()
        credit.total_credits_used += amount
        credit.save()
    
    return True

def can_use_feature(cost=1):
    """Check if project has enough non-expired credits for a feature"""
    from django.db.models import Sum
    
    available_credits = CreditHistory.objects.filter(
        transaction_type='purchase',
        expires_at__gt=timezone.now(),
        amount__gt=0
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    return available_credits >= cost

def get_credit_stats():
    """Get complete credit statistics"""
    credit = get_credit_balance()
    
    # Calculate actual available balance (non-expired)
    current_balance = credit.get_current_balance()
    
    return {
        'current_balance': current_balance,
        'total_added_this_month': credit.total_credits_added,
        'total_used_this_month': credit.total_credits_used,
        'last_reset': credit.last_reset_date,
        'net_usage': credit.total_credits_added - credit.total_credits_used
    }

def expire_old_credits():
    """Automatically expire credits that have passed their expiry date"""
    from django.utils import timezone
    
    expired_credits = CreditHistory.objects.filter(
        transaction_type='purchase',
        expires_at__lte=timezone.now(),
        amount__gt=0
    )
    
    total_expired = 0
    for credit in expired_credits:
        # Record expiration
        CreditHistory.objects.create(
            transaction_type='expiration',
            amount=0,
            description=f"Credit expiration: {credit.amount} credits expired",
            user=None
        )
        total_expired += credit.amount
        credit.amount = 0  # Set to zero since expired
        credit.save()
    
    return total_expired

# Keep your existing reset functions but they work differently now
def reset_monthly_counters():
    """Reset monthly counters only (credits now expire individually)"""
    with transaction.atomic():
        credit = get_credit_balance()
        
        # Record reset in history
        if credit.total_credits_added > 0 or credit.total_credits_used > 0:
            CreditHistory.objects.create(
                transaction_type='monthly_reset',
                amount=0,
                description=f"Monthly counter reset - Added: {credit.total_credits_added}, Used: {credit.total_credits_used}"
            )
        
        # Reset counters only (credits expire individually now)
        credit.total_credits_added = 0
        credit.total_credits_used = 0
        credit.last_reset_date = timezone.now()
        credit.save()
    
    return True


## History
def get_credit_history(days=30, transaction_type=None):
    """Get credit history with filters"""
    from django.utils import timezone
    from datetime import timedelta
    
    queryset = CreditHistory.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=days)
    )
    
    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)
    
    return queryset.order_by('-created_at')

def get_monthly_summary():
    """Get summary of current month's credit activity"""
    credit = get_credit_balance()
    history_this_month = CreditHistory.objects.filter(
        created_at__gte=credit.last_reset_date
    ).exclude(transaction_type='monthly_reset')

    # Calculate actual available balance (non-expired)
    current_balance = credit.get_current_balance()
    
    return {
        'balance': current_balance,
        'added_this_month': credit.total_credits_added,
        'used_this_month': credit.total_credits_used,
        'transactions_count': history_this_month.count(),
        'last_reset': credit.last_reset_date
    }
