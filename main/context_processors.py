from .models import Notification
from django.core.cache import cache


def unread_notifications(request):
    """Returns the unread notification count for the authenticated user with caching."""
    unread_notifications_count = 0
    if request.user.is_authenticated:
        # Cache the count for 30 seconds to reduce database queries
        cache_key = f'unread_notifications_{request.user.id}'
        unread_notifications_count = cache.get(cache_key)
        
        if unread_notifications_count is None:
            unread_notifications_count = Notification.objects.filter(
                receiver=request.user, 
                read=False
            ).count()
            cache.set(cache_key, unread_notifications_count, 30)  # Cache for 30 seconds
    
    return {
        'unread_notifications_count': unread_notifications_count
    }
