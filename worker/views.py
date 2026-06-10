from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from core.models import Order, Bonus, LoyaltyToken
from worker.models import ServiceAd
from accounts.models import User
from decimal import Decimal
from .models import WorkSchedule
from .forms import ServiceAdForm, WorkScheduleForm
from functools import wraps


def worker_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_worker:
            messages.error(request, "Ruxsat yo'q.")
            return redirect('accounts:role_redirect')
        if not request.user.is_approved:
            return redirect('accounts:pending_approval')
        return view_func(request, *args, **kwargs)
    return wrapper

@worker_required
def scheduled_orders(request):
    """Ishchi uchun oldindan belgilangan buyurtmalar"""
    from django.utils import timezone
    from core.models import Order

    upcoming = Order.objects.filter(
        service_ad__worker=request.user,
        status='pending',
        scheduled_time__gte=timezone.now()
    ).order_by('scheduled_time')

    context = {'upcoming': upcoming}
    return render(request, 'worker/scheduled_orders.html', context)


@worker_required
def schedule_list(request):
    from .models import WorkSchedule

    # Barcha 7 kun uchun ma'lumot tayyorlaymiz
    weekdays = [
        (0, 'Dushanba'),
        (1, 'Seshanba'),
        (2, 'Chorshanba'),
        (3, 'Payshanba'),
        (4, 'Juma'),
        (5, 'Shanba'),
        (6, 'Yakshanba'),
    ]

    existing = {s.weekday: s for s in WorkSchedule.objects.filter(worker=request.user)}

    # Template uchun birlashtilgan list
    schedule_days = []
    for day_num, day_name in weekdays:
        schedule_days.append({
            'day_num': day_num,
            'day_name': day_name,
            'schedule': existing.get(day_num),  # None yoki WorkSchedule obyekti
        })

    return render(request, 'worker/schedule.html', {'schedule_days': schedule_days})


@worker_required
def schedule_create(request):
    """Yangi ish kuni qo'shish"""
    if request.method == 'POST':
        form = WorkScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.worker = request.user
            # Mavjud bo'lsa yangilash
            existing = WorkSchedule.objects.filter(
                worker=request.user,
                weekday=schedule.weekday
            ).first()
            if existing:
                existing.start_time = schedule.start_time
                existing.end_time   = schedule.end_time
                existing.is_active  = schedule.is_active
                existing.save()
                messages.success(request, "Jadval yangilandi!")
            else:
                schedule.save()
                messages.success(request, "Jadval saqlandi!")
            return redirect('worker:schedule_list')
    else:
        form = WorkScheduleForm()
    return render(request, 'worker/schedule_form.html', {'form': form})


@worker_required
def schedule_toggle(request, pk):
    """Ish kunini yoqish/o'chirish"""
    schedule = get_object_or_404(WorkSchedule, pk=pk, worker=request.user)
    schedule.is_active = not schedule.is_active
    schedule.save()
    status = "yoqildi" if schedule.is_active else "o'chirildi"
    messages.success(request, f"{schedule.get_weekday_display()} {status}!")
    return redirect('worker:schedule_list')

@worker_required
def dashboard(request):
    all_orders       = Order.objects.filter(worker=request.user)
    completed_orders = all_orders.filter(status=Order.Status.COMPLETED)
    pending_orders   = all_orders.filter(status=Order.Status.PENDING).select_related('customer','car','service_ad')
    loyalty, _       = LoyaltyToken.objects.get_or_create(user=request.user)

    # ✅ Decimal bilan hisoblash
    total_sum  = completed_orders.aggregate(t=Sum('total_price'))['t'] or Decimal('0')
    earnings   = int(total_sum * Decimal('50') // Decimal('100'))

    this_month = timezone.now().replace(day=1).date()
    monthly_sum = completed_orders.filter(
        completed_at__date__gte=this_month
    ).aggregate(t=Sum('total_price'))['t'] or Decimal('0')
    monthly_earnings = int(monthly_sum * Decimal('50') // Decimal('100'))

    from datetime import date, timedelta
    week_data = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        cnt = completed_orders.filter(completed_at__date=d).count()
        day_sum = completed_orders.filter(
            completed_at__date=d
        ).aggregate(t=Sum('total_price'))['t'] or Decimal('0')
        earn = int(day_sum * Decimal('50') // Decimal('100'))
        week_data.append({'date': d.strftime('%d.%m'), 'count': cnt, 'earn': earn})

    return render(request, 'worker/dashboard.html', {
        'total_orders':      all_orders.count(),
        'completed_orders':  completed_orders.count(),
        'rejected_orders':   all_orders.filter(status=Order.Status.REJECTED).count(),
        'pending_count':     pending_orders.count(),
        'loyalty_balance':   loyalty.balance,
        'total_earnings':    earnings,
        'monthly_earnings':  monthly_earnings,
        'pending_orders':    pending_orders[:5],
        'week_data':         week_data,
        'rating':            request.user.worker_rating,
    })

@worker_required
def my_ads(request):
    ads = ServiceAd.objects.filter(worker=request.user)
    return render(request, 'worker/my_ads.html', {'ads': ads})

# worker/views.py

from django.core.exceptions import ValidationError
from django.contrib import messages

@worker_required
def create_ad(request):
    if request.method == 'POST':
        form = ServiceAdForm(request.POST)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.worker = request.user
            ad.full_clean()   # clean() da narx tekshiriladi (ValidationError)
            ad.save()
            messages.success(request, "E'lon muvaffaqiyatli yaratildi!")
            return redirect('worker:my_ads')
        else:
            # form xatoliklari allaqachon mavjud
            pass
    else:
        form = ServiceAdForm()
    return render(request, 'worker/ad_create.html', {'form': form})
@worker_required
def edit_ad(request, pk):
    ad = get_object_or_404(ServiceAd, pk=pk, worker=request.user)
    if request.method == 'POST':
        form = ServiceAdForm(request.POST, instance=ad)
        if form.is_valid():
            ad = form.save(commit=False)
            ad.full_clean()   # narx validatsiyasi
            ad.save()
            messages.success(request, "E'lon yangilandi!")
            return redirect('worker:my_ads')
        # form xatoliklari avtomatik ko‘rsatiladi
    else:
        form = ServiceAdForm(instance=ad)
    return render(request, 'worker/ad_edit.html', {'form': form, 'ad': ad})

@worker_required
def delete_ad(request, pk):
    if request.method == 'POST':
        get_object_or_404(ServiceAd, pk=pk, worker=request.user).delete()
        messages.success(request, "E'lon o'chirildi.")
    return redirect('worker:my_ads')


@worker_required
def orders(request):
    involved = Q(worker=request.user) | Q(helper_2=request.user) | Q(helper_3=request.user)
    orders_qs = Order.objects.filter(
        involved,
        status__in=[Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.IN_PROGRESS],
    ).select_related('customer','car','service_ad','worker','helper_2','helper_3').order_by('-created_at')

    # Yordamchi sifatida bog'langanlarni belgilab qo'yamiz
    orders_list = []
    for o in orders_qs:
        o.is_helper = (o.worker_id != request.user.id)
        orders_list.append(o)

    # Asosiy ishchi sifatida yordamchi qo'shish uchun mavjud ishchilar ro'yxati
    available_workers = User.objects.filter(
        role='worker', is_approved=True
    ).exclude(id=request.user.id).order_by('first_name', 'last_name')

    return render(request, 'worker/orders.html', {
        'orders': orders_list,
        'available_workers': available_workers,
    })


@worker_required
def accept_order(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk, worker=request.user)
        if order.status == Order.Status.PENDING:
            order.status = Order.Status.ACCEPTED
            order.accepted_at = timezone.now()
            order.save()
            # E'lon `is_active` ni o'zgartirmaymiz — ishchi band/bo'sh ekani
            # `worker_is_busy` annotation (Exists subquery) orqali aniqlanadi.
            messages.success(request, "Buyurtma qabul qilindi!")
    return redirect('worker:orders')


@worker_required
def reject_order(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk, worker=request.user)
        if order.status == Order.Status.PENDING:
            order.status = Order.Status.REJECTED
            order.save()
            messages.info(request, "Buyurtma rad etildi.")
    return redirect('worker:orders')


@worker_required
def complete_order(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk, worker=request.user)
        if order.status == Order.Status.ACCEPTED:
            # ✅ Mashina turiga mos minimal vaqt o'tgan bo'lishi shart
            if not order.can_be_completed():
                left = order.minutes_left_to_complete()
                need = order.required_work_minutes()
                tur  = "yuk mashina" if order.is_heavy_wash() else "yengil mashina"
                messages.warning(
                    request,
                    f"Buyurtmani yakunlash uchun qabul qilingandan beri kamida "
                    f"{need} daqiqa o'tishi kerak ({tur}). "
                    f"Yana ~{left} daqiqa kuting."
                )
                return redirect('worker:orders')

            order.status = Order.Status.COMPLETED
            order.completed_at = timezone.now()
            order.save()
            # E'lon avtomatik "bo'sh" holatga qaytadi — boshqa faol buyurtmasi
            # bo'lmasa worker_is_busy = False bo'ladi.
            messages.success(request, "Buyurtma yakunlandi! Tanga yig'ildi 🪙")
    return redirect('worker:orders')


@worker_required
def add_helper(request, pk):
    """Asosiy ishchi buyurtmaga yordamchi qo'shadi (slot: 2 yoki 3)."""
    if request.method != 'POST':
        return redirect('worker:orders')

    order = get_object_or_404(Order, pk=pk, worker=request.user)

    if order.status in (Order.Status.COMPLETED, Order.Status.REJECTED, Order.Status.CANCELLED):
        messages.error(request, "Yopilgan buyurtmaga yordamchi qo'shib bo'lmaydi.")
        return redirect('worker:orders')

    try:
        helper_id = int(request.POST.get('helper_id', '0'))
    except (TypeError, ValueError):
        helper_id = 0

    if not helper_id:
        messages.error(request, "Ishchini tanlang.")
        return redirect('worker:orders')

    if helper_id == request.user.id:
        messages.error(request, "O'zingizni yordamchi qilib qo'sha olmaysiz.")
        return redirect('worker:orders')

    if helper_id in (order.helper_2_id, order.helper_3_id):
        messages.warning(request, "Bu ishchi allaqachon yordamchi sifatida qo'shilgan.")
        return redirect('worker:orders')

    helper = User.objects.filter(id=helper_id, role='worker', is_approved=True).first()
    if not helper:
        messages.error(request, "Ishchi topilmadi.")
        return redirect('worker:orders')

    # Bo'sh slotni topamiz: avval helper_2, keyin helper_3
    if not order.helper_2_id:
        order.helper_2 = helper
        slot = 2
    elif not order.helper_3_id:
        order.helper_3 = helper
        slot = 3
    else:
        messages.warning(request, "Bu buyurtmada yordamchi joylari to'lgan (2 ta).")
        return redirect('worker:orders')

    order.save(update_fields=['helper_2' if slot == 2 else 'helper_3', 'updated_at'])
    messages.success(request, f"{helper.get_full_name() or helper.email} yordamchi sifatida qo'shildi.")
    return redirect('worker:orders')


@worker_required
def remove_helper(request, pk, slot):
    """Asosiy ishchi yordamchini olib tashlaydi."""
    if request.method != 'POST':
        return redirect('worker:orders')

    if slot not in (2, 3):
        messages.error(request, "Noto'g'ri yordamchi o'rni.")
        return redirect('worker:orders')

    order = get_object_or_404(Order, pk=pk, worker=request.user)

    field = f'helper_{slot}'
    if not getattr(order, f'{field}_id'):
        messages.warning(request, "Bu o'rinda yordamchi yo'q edi.")
        return redirect('worker:orders')

    setattr(order, field, None)
    order.save(update_fields=[field, 'updated_at'])
    messages.info(request, "Yordamchi olib tashlandi.")
    return redirect('worker:orders')


@worker_required
def order_history(request):
    involved = Q(worker=request.user) | Q(helper_2=request.user) | Q(helper_3=request.user)
    orders_qs = Order.objects.filter(
        involved,
        status__in=[Order.Status.COMPLETED, Order.Status.REJECTED, Order.Status.CANCELLED],
    ).select_related('customer','car','service_ad','worker','helper_2','helper_3').prefetch_related('review').order_by('-created_at')

    orders_list = []
    for o in orders_qs:
        o.is_helper = (o.worker_id != request.user.id)
        orders_list.append(o)

    return render(request, 'worker/order_history.html', {'orders': orders_list})


@worker_required
def bonuses(request):
    loyalty, _ = LoyaltyToken.objects.get_or_create(user=request.user)
    bonuses_list = Bonus.objects.filter(is_active=True).order_by('token_cost')

    # Tanga tarixi
    from core.models import LoyaltyTransaction
    transactions = LoyaltyTransaction.objects.filter(loyalty=loyalty).order_by('-created_at')[:10]

    return render(request, 'worker/bonuses.html', {
        'bonuses':      bonuses_list,
        'loyalty':      loyalty,
        'transactions': transactions,
    })


@worker_required
def claim_bonus(request, pk):
    if request.method == 'POST':
        bonus = get_object_or_404(Bonus, pk=pk)
        success, msg = bonus.claim(request.user)
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    return redirect('worker:bonuses')


@worker_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name','').strip()
        user.last_name  = request.POST.get('last_name','').strip()
        user.phone      = request.POST.get('phone','').strip()
        if request.FILES.get('avatar'):
            user.avatar = request.FILES['avatar']
        user.save()
        messages.success(request, "Profil yangilandi!")
        return redirect('worker:profile')
    return render(request, 'worker/profile.html')
