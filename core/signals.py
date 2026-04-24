from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from accounts.models import User
from core.models import Order, LoyaltyToken, LoyaltyTransaction


@receiver(post_save, sender=User)
def create_loyalty_token(sender, instance, created, **kwargs):
    if created:
        LoyaltyToken.objects.get_or_create(user=instance)


@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    from core.notifications import (
        notify_new_order, notify_order_accepted,
        notify_order_rejected, notify_order_completed
    )

    if created:
        notify_new_order(instance)
        return

    if instance.status == Order.Status.ACCEPTED:
        notify_order_accepted(instance)

    elif instance.status == Order.Status.REJECTED:
        notify_order_rejected(instance)

    elif instance.status == Order.Status.COMPLETED:
        notify_order_completed(instance)
        _award_tokens(instance)
        _add_online_income(instance)   # ✅ Avtomatik 50% kirim


def _award_tokens(order):
    tokens = getattr(settings, 'LOYALTY_TOKENS_PER_ORDER', 10)
    for user in [order.customer, order.worker]:
        loyalty, _ = LoyaltyToken.objects.get_or_create(user=user)
        already = LoyaltyTransaction.objects.filter(
            loyalty=loyalty, order=order,
            tx_type=LoyaltyTransaction.TxType.EARN
        ).exists()
        if not already:
            loyalty.add_tokens(tokens)
            LoyaltyTransaction.objects.create(
                loyalty=loyalty,
                tx_type=LoyaltyTransaction.TxType.EARN,
                amount=tokens,
                description=f"Buyurtma #{order.pk} yakunlandi",
                order=order
            )


def _add_online_income(order):
    """Muvaffaqiyatli onlayn buyurtmadan 50% kirimi avtomatik qo'shish"""
    try:
        from finance.models import Income
        from django.utils import timezone

        already = Income.objects.filter(
            order=order, category=Income.Category.ONLINE
        ).exists()

        if not already and order.total_price:
            auto_amount = int(order.total_price * 50 / 100)
            inc_date = order.completed_at.date() if order.completed_at else timezone.now().date()
            Income.objects.create(
                category=Income.Category.ONLINE,
                description=f"Onlayn buyurtma #{order.pk} — {order.customer.get_full_name()}",
                amount=auto_amount,
                order=order,
                date=inc_date,
            )
    except Exception:
        pass  # Finance app bo'lmasa — o'tkazib yuborsin


@receiver(post_save, sender=User)
def notify_worker_events(sender, instance, created, **kwargs):
    if created:
        return
    from core.notifications import notify_new_worker_request, notify_worker_approved
    if instance.role == 'worker' and not instance.is_approved:
        from core.models import Notification
        already = Notification.objects.filter(
            notif_type='new_worker',
            message__icontains=instance.get_full_name()
        ).exists()
        if not already:
            notify_new_worker_request(instance)
    elif instance.role == 'worker' and instance.is_approved:
        from core.models import Notification
        already = Notification.objects.filter(
            user=instance, notif_type='worker_approved'
        ).exists()
        if not already:
            notify_worker_approved(instance)
