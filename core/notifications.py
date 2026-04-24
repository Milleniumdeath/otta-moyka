from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def send_notification(user, title, message, icon='fa-bell', color='cyan', url='#', notif_type='info'):
    """
    Foydalanuvchiga real vaqtda bildirishnoma yuborish.

    Ishlatish:
        send_notification(
            user=worker_user,
            title="Yangi buyurtma!",
            message="Jasur Karimov buyurtma berdi",
            icon='fa-clipboard-list',
            color='cyan',
            url='/worker/orders/'
        )
    """
    from core.models import Notification

    # DB ga saqlash
    Notification.objects.create(
        user=user,
        notif_type=notif_type,
        title=title,
        message=message,
        icon=icon,
        color=color,
        url=url,
    )

    # WebSocket orqali real vaqtda yuborish
    channel_layer = get_channel_layer()
    group_name = f'notifications_{user.id}'

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type':    'notification_message',
                'title':   title,
                'message': message,
                'icon':    icon,
                'color':   color,
                'url':     url,
            }
        )
    except Exception:
        # Redis ulanmagan bo'lsa — faqat DB ga saqlanadi
        pass


def notify_new_order(order):
    """Ishchiga yangi buyurtma haqida xabar"""
    send_notification(
        user=order.worker,
        title="Yangi buyurtma!",
        message=f"{order.customer.get_full_name()} buyurtma berdi — {order.car}",
        icon='fa-clipboard-list',
        color='cyan',
        url='/worker/orders/',
        notif_type='new_order',
    )
    # Moyka egasiga ham xabar
    from accounts.models import User
    owner = User.objects.filter(role='owner').first()
    if owner:
        send_notification(
            user=owner,
            title="Yangi buyurtma",
            message=f"#{order.id} — {order.customer.get_full_name()} → {order.worker.get_full_name()}",
            icon='fa-receipt',
            color='amber',
            url='/owner/dashboard/',
            notif_type='new_order',
        )


def notify_order_accepted(order):
    """Mijozga buyurtma qabul qilingani haqida"""
    send_notification(
        user=order.customer,
        title="Buyurtma qabul qilindi!",
        message=f"{order.worker.get_full_name()} buyurtmangizni qabul qildi",
        icon='fa-circle-check',
        color='green',
        url='/customer/orders/history/',
        notif_type='order_accept',
    )


def notify_order_rejected(order):
    """Mijozga buyurtma rad etilgani haqida"""
    send_notification(
        user=order.customer,
        title="Buyurtma rad etildi",
        message=f"{order.worker.get_full_name()} buyurtmangizni rad etdi",
        icon='fa-circle-xmark',
        color='red',
        url='/customer/orders/',
        notif_type='order_reject',
    )


def notify_order_completed(order):
    """Buyurtma yakunlanganda ikkalasiga xabar"""
    # Mijozga
    send_notification(
        user=order.customer,
        title="Buyurtma yakunlandi! 🎉",
        message=f"Yuvish tugadi! +10 tanga yig'ildi. Bahoyingizni bildiring",
        icon='fa-flag-checkered',
        color='green',
        url='/customer/orders/history/',
        notif_type='order_done',
    )
    # Ishchiga
    send_notification(
        user=order.worker,
        title="Buyurtma yakunlandi! 🪙",
        message=f"#{order.id} buyurtma yakunlandi — +10 tanga yig'ildi",
        icon='fa-coins',
        color='amber',
        url='/worker/orders/history/',
        notif_type='order_done',
    )


def notify_new_worker_request(worker):
    """Moyka egasiga yangi ishchi so'rovi"""
    from accounts.models import User
    owner = User.objects.filter(role='owner').first()
    if owner:
        send_notification(
            user=owner,
            title="Yangi ishchi so'rovi!",
            message=f"{worker.get_full_name()} — {worker.phone} ishchi bo'lmoqchi",
            icon='fa-user-plus',
            color='amber',
            url='/owner/workers/',
            notif_type='new_worker',
        )


def notify_worker_approved(worker):
    """Ishchiga tasdiqlangani haqida"""
    send_notification(
        user=worker,
        title="Siz tasdiqlandi! 🎉",
        message="Moyka egasi tomonidan tasdiqlandi. Endi ishlashingiz mumkin!",
        icon='fa-user-check',
        color='green',
        url='/worker/dashboard/',
        notif_type='worker_approved',
    )
