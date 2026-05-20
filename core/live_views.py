"""Yengil polling endpoint — sahifani avtomatik yangilash uchun.

Klient har 5–10 sek bir marta /api/live-digest/ ga so'rov yuboradi. Backend
foydalanuvchi roli bo'yicha buyurtmalar va bildirishnomalar "signaturasini"
qaytaradi. Klient saqlangan signatura bilan solishtirib, o'zgarish bo'lsa
sahifani yangilaydi.
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.http import JsonResponse

from core.models import Notification, Order


def _orders_signature(qs):
    """Buyurtmalar holatini yengil yig'ma signatura qiladi.

    max(id) + har bir status bo'yicha sanoq → har qanday status o'zgarishi
    yoki yangi buyurtma kelishi signaturani o'zgartiradi.
    """
    max_id = qs.aggregate(m=Max('id'))['m'] or 0
    by_status = qs.values('status').annotate(c=Count('id'))
    counts = sorted((row['status'], row['c']) for row in by_status)
    counts_str = ','.join(f"{s}:{c}" for s, c in counts)
    return f"{max_id}|{counts_str}"


@login_required
def live_digest(request):
    user = request.user
    role = getattr(user, 'role', '')

    if role == 'worker':
        qs = Order.objects.filter(
            worker=user,
            status__in=[
                Order.Status.PENDING,
                Order.Status.ACCEPTED,
                Order.Status.IN_PROGRESS,
            ],
        )
    elif role == 'customer':
        qs = Order.objects.filter(customer=user)
    elif role == 'owner' or user.is_superuser:
        qs = Order.objects.all()
    else:
        qs = Order.objects.none()

    return JsonResponse({
        'orders_sig':     _orders_signature(qs),
        'unread_notifs':  Notification.objects.filter(
            user=user, is_read=False
        ).count(),
    })
