from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        unread = Notification.objects.filter(
            recipient=request.user, is_read=False
        )
        return {
            "notification_count": unread.count(),
            "notifications": unread[:5],
        }
    return {}
