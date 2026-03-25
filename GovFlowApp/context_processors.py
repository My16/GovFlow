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


from .models import Document
from django.db.models import Q

def user_documents(request):
    """
    Provides documents for the current user to populate dropdowns, e.g., per-document report.
    """
    if request.user.is_authenticated:
        documents = Document.objects.filter(
            Q(sender=request.user) | Q(current_office=request.user)
        ).order_by('-created_at')
        return {
            "user_documents": documents
        }
    return {}