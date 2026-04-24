from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from core.models import Notification


@login_required
def get_notifications(request):
    """So'nggi 20 ta bildirishnoma"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]

    return JsonResponse({
        'notifications': [
            {
                'id':      n.id,
                'title':   n.title,
                'message': n.message,
                'icon':    n.icon,
                'color':   n.color,
                'url':     n.url,
                'is_read': n.is_read,
                'time':    n.created_at.strftime('%H:%M'),
                'date':    n.created_at.strftime('%d.%m.%Y'),
            }
            for n in notifications
        ],
        'unread_count': Notification.objects.filter(
            user=request.user, is_read=False
        ).count(),
    })


@login_required
@require_POST
def mark_read(request):
    """Barcha bildirishnomalarni o'qilgan deb belgilash"""
    Notification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse({'status': 'ok'})
