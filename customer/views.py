from django.db.models import Sum
from core.models import Order, Bonus, LoyaltyToken, Review, Receipt, Reminder
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from worker.models import ServiceAd, WorkSchedule
from customer.models import Car
from customer.forms import *


def customer_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_customer:
            messages.error(request, "Ruxsat yo'q.")
            return redirect('accounts:role_redirect')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@customer_required
def dashboard(request):
    all_orders    = Order.objects.filter(customer=request.user)
    completed     = all_orders.filter(status=Order.Status.COMPLETED)
    active_orders = all_orders.filter(
        status__in=[Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.IN_PROGRESS]
    ).select_related('worker','car','service_ad')
    loyalty, _    = LoyaltyToken.objects.get_or_create(user=request.user)

    # Jami sarf: barcha yakunlangan buyurtmalar summasining 100%
    total_spent = completed.aggregate(t=Sum('total_price'))['t'] or 0

    # Oylik sarf
    this_month = timezone.now().replace(day=1).date()
    monthly_spent = completed.filter(
        completed_at__date__gte=this_month
    ).aggregate(t=Sum('total_price'))['t'] or 0

    # So'nggi 7 kun
    from datetime import date, timedelta
    week_data = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        cnt  = completed.filter(completed_at__date=d).count()
        spent = int(completed.filter(completed_at__date=d).aggregate(t=Sum('total_price'))['t'] or 0)
        week_data.append({'date': d.strftime('%d.%m'), 'count': cnt, 'spent': spent})

    return render(request, 'customer/dashboard.html', {
        'total_orders':    all_orders.count(),
        'completed_orders': completed.count(),
        'cars_count':      Car.objects.filter(owner=request.user).count(),
        'loyalty_balance': loyalty.balance,
        'total_spent':     total_spent,
        'monthly_spent':   monthly_spent,
        'active_orders':   active_orders,
        'week_data':       week_data,
    })


@customer_required
def my_cars(request):
    cars = Car.objects.filter(owner=request.user)
    return render(request, 'customer/my_cars.html', {'cars': cars})


@customer_required
def add_car(request):
    if request.method == 'POST':
        brand=request.POST.get('brand','').strip()
        model=request.POST.get('model','').strip()
        plate_number=request.POST.get('plate_number','').strip()
        car_type=request.POST.get('car_type','light')
        image=request.FILES.get('image')
        if not all([brand, model, plate_number]):
            messages.error(request, "Barcha maydonlarni to'ldiring.")
            return redirect('customer:my_cars')
        Car.objects.create(owner=request.user, brand=brand, model=model, plate_number=plate_number, car_type=car_type, image=image)
        messages.success(request, f"{brand} {model} qo'shildi!")
    return redirect('customer:my_cars')


@customer_required
def edit_car(request, pk):
    car = get_object_or_404(Car, pk=pk, owner=request.user)
    if request.method == 'POST':
        car.brand=request.POST.get('brand',car.brand).strip()
        car.model=request.POST.get('model',car.model).strip()
        car.plate_number=request.POST.get('plate_number',car.plate_number).strip()
        car.car_type=request.POST.get('car_type',car.car_type)
        if request.FILES.get('image'): car.image=request.FILES['image']
        car.save()
        messages.success(request, "Mashina yangilandi!")
        return redirect('customer:my_cars')
    return render(request, 'customer/car_edit.html', {'car': car})


@customer_required
def delete_car(request, pk):
    if request.method == 'POST':
        get_object_or_404(Car, pk=pk, owner=request.user).delete()
        messages.success(request, "Mashina o'chirildi.")
    return redirect('customer:my_cars')


@customer_required
def orders(request):
    """Mijoz buyurtma berish sahifasi - mashina turiga mos e'lonlar"""
    from worker.models import ServiceAd
    from customer.models import Car

    cars = Car.objects.filter(owner=request.user)

    # Tanlangan mashina (default: birinchisi)
    selected_car_id = request.GET.get('car_id')
    selected_car = None

    if selected_car_id:
        selected_car = cars.filter(pk=selected_car_id).first()
    elif cars.exists():
        selected_car = cars.first()

    # Mashina turiga qarab e'lonlarni filtrlaymiz
    from django.db.models import Avg, Count, F, Exists, OuterRef, Subquery, IntegerField
    from django.db.models.functions import Coalesce
    # Ishchi band bo'lsa (qabul qilgan yoki jarayondagi buyurtmasi bo'lsa)
    # — e'londa "band" deb ko'rsatamiz. PENDING band hisoblanmaydi: ishchi
    # hali tanlash bosqichida, bir vaqtda bir necha so'rov turishi mumkin.
    busy_subq = Order.objects.filter(
        worker_id=OuterRef('worker_id'),
        status__in=[
            Order.Status.ACCEPTED,
            Order.Status.IN_PROGRESS,
        ],
    )
    # Ishchining navbatidagi PENDING buyurtmalar soni (faqat sanash uchun
    # subquery — ServiceAd asosiy queryga ta'sir qilmaydi).
    queue_subq = Order.objects.filter(
        worker_id=OuterRef('worker_id'),
        status=Order.Status.PENDING,
    ).order_by().values('worker_id').annotate(c=Count('id')).values('c')
    ads_qs = ServiceAd.objects.filter(is_active=True).select_related('worker').annotate(
        worker_avg=Avg('worker__worker_orders__review__rating'),
        worker_reviews=Count('worker__worker_orders__review', distinct=True),
        worker_is_busy=Exists(busy_subq),
        worker_queue_count=Coalesce(
            Subquery(queue_subq, output_field=IntegerField()),
            0,
        ),
    ).order_by(F('worker_avg').desc(nulls_last=True), '-created_at')

    if selected_car:
        if selected_car.car_type == 'heavy':
            # Yuk mashina faqat "heavy" e'lonlarni ko'radi
            ads_qs = ads_qs.filter(service_type='heavy')
        else:
            # Yengil mashina "heavy" e'lonlarni ko'rmaydi
            ads_qs = ads_qs.exclude(service_type='heavy')

    # Bir ishchining bir xil xizmat turidagi bir nechta reklamasi bo'lsa,
    # eng yaxshi reytingli/yangi reklamani tanlaymiz. Reyting bo'yicha tartiblangani uchun
    # birinchi uchragan (ishchi, xizmat) juftligi eng yaxshisi.
    seen_keys = set()
    ads = []
    for ad in ads_qs:
        key = (ad.worker_id, ad.service_type)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        ads.append(ad)

    context = {
        'cars':         cars,
        'selected_car': selected_car,
        'ads':          ads,
    }
    return render(request, 'customer/orders.html', context)


@customer_required
def book_order(request, ad_pk):
    """Avval to'lov, keyin buyurtma — Order + Receipt atomik yaratiladi."""
    if request.method != 'POST':
        return redirect('customer:orders')

    from django.db import transaction

    ad     = get_object_or_404(ServiceAd, pk=ad_pk, is_active=True)
    car_id = request.POST.get('car_id')
    note   = request.POST.get('note', '').strip()
    scheduled = request.POST.get('scheduled_time')

    # — Buyurtma maydonlari validatsiyasi —
    if not car_id:
        messages.error(request, "Mashina tanlang.")
        return redirect('customer:orders')

    car = get_object_or_404(Car, pk=car_id, owner=request.user)

    # Bir mijoz bir ishchiga faol buyurtma turgan bo'lsa, dublikat oldi olinadi
    already = Order.objects.filter(
        customer=request.user,
        worker=ad.worker,
        status__in=[
            Order.Status.PENDING,
            Order.Status.ACCEPTED,
            Order.Status.IN_PROGRESS,
        ],
    ).exists()
    if already:
        messages.warning(
            request,
            "Bu ishchida sizning faol buyurtmangiz allaqachon bor. "
            "Avval u yakunlansin yoki bekor qiling."
        )
        return redirect('customer:order_history')

    # Mashina turi
    if ad.service_type == 'heavy' and car.car_type != 'heavy':
        messages.error(request, "Bu e'lon faqat yuk mashinalar uchun!")
        return redirect('customer:orders')
    if ad.service_type != 'heavy' and car.car_type == 'heavy':
        messages.error(request, "Yuk mashina uchun faqat 'Yuk transport' e'lonlaridan buyurtma bering!")
        return redirect('customer:orders')

    # Ish vaqti
    if scheduled:
        from datetime import datetime
        scheduled_dt = datetime.fromisoformat(scheduled)
        weekday = scheduled_dt.weekday()
        schedule = WorkSchedule.objects.filter(
            worker=ad.worker,
            weekday=weekday,
            is_active=True,
        ).first()
        if not schedule:
            messages.warning(request, "Ishchi bu kuni ishlamaydi. Boshqa kun tanlang.")
            return redirect('customer:orders')
        if not (schedule.start_time <= scheduled_dt.time() <= schedule.end_time):
            messages.warning(
                request,
                f"Ishchi bu kuni {schedule.start_time.strftime('%H:%M')}–"
                f"{schedule.end_time.strftime('%H:%M')} oralig'ida ishlaydi."
            )
            return redirect('customer:orders')

    # — To'lov maydonlari validatsiyasi (online to'lov, soxta) —
    method = request.POST.get('method', Receipt.Method.CARD)
    if method not in dict(Receipt.Method.choices):
        method = Receipt.Method.CARD

    card_number = ''.join(c for c in request.POST.get('card_number', '') if c.isdigit())
    holder      = request.POST.get('holder_name', '').strip()[:80]

    if method == Receipt.Method.CARD:
        if len(card_number) < 12:
            messages.error(request, "Karta raqamini to'liq kiriting (kamida 12 raqam).")
            return redirect('customer:orders')
        if not holder:
            messages.error(request, "Karta egasi ismini kiriting.")
            return redirect('customer:orders')

    # — Atomik yaratish: Order + Receipt —
    with transaction.atomic():
        order = Order.objects.create(
            customer=request.user,
            worker=ad.worker,
            car=car,
            service_ad=ad,
            note=note,
            total_price=ad.price,
            status=Order.Status.PENDING,
            scheduled_time=scheduled,
        )
        receipt = Receipt.objects.create(
            order=order,
            customer=request.user,
            amount=ad.price,
            method=method,
            card_last4=card_number[-4:] if card_number else '',
            holder_name=holder,
            transaction_id=Receipt.generate_txn_id(),
        )

    # Oxirgi 3 ta chek saqlansin
    Receipt.prune_old(request.user)

    pos = order.queue_position()
    if pos and pos > 1:
        messages.success(
            request,
            f"To'lov amalga oshirildi va navbatga yozildingiz — siz {pos}-o'rindasiz."
        )
    else:
        messages.success(request, "To'lov amalga oshirildi! Buyurtma berildi.")

    return redirect('customer:receipt_detail', pk=receipt.pk)


@customer_required
def order_history(request):
    orders_list = Order.objects.filter(customer=request.user).select_related(
        'worker','car','service_ad','receipt'
    ).prefetch_related('review').order_by('-created_at')
    return render(request, 'customer/order_history.html', {'orders': orders_list})


@customer_required
def add_review(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk, customer=request.user, status=Order.Status.COMPLETED)
        if not hasattr(order, 'review'):
            Review.objects.create(
                order=order, reviewer=request.user,
                rating=max(1, min(5, int(request.POST.get('rating',5)))),
                comment=request.POST.get('comment','')
            )
            messages.success(request, "Bahoyingiz saqlandi!")
        else:
            messages.info(request, "Allaqachon baholagansiz.")
    return redirect('customer:order_history')


@customer_required
def bonuses(request):
    loyalty, _ = LoyaltyToken.objects.get_or_create(user=request.user)
    bonuses_list = Bonus.objects.filter(is_active=True).order_by('token_cost')

    # Tanga tarixi
    from core.models import LoyaltyTransaction
    transactions = LoyaltyTransaction.objects.filter(loyalty=loyalty).order_by('-created_at')[:10]

    return render(request, 'customer/bonuses.html', {
        'bonuses':      bonuses_list,
        'loyalty':      loyalty,
        'transactions': transactions,
    })


@customer_required
def claim_bonus(request, pk):
    if request.method == 'POST':
        bonus = get_object_or_404(Bonus, pk=pk)
        success, msg = bonus.claim(request.user)
        if success: messages.success(request, msg)
        else: messages.error(request, msg)
    return redirect('customer:bonuses')


@customer_required
def receipt_detail(request, pk):
    """Bitta chekni ko'rsatish."""
    receipt = get_object_or_404(Receipt, pk=pk, customer=request.user)
    return render(request, 'customer/receipt.html', {'receipt': receipt})


@customer_required
def receipts_list(request):
    """Mijozning oxirgi 3 ta cheki."""
    receipts = Receipt.objects.filter(
        customer=request.user
    ).select_related('order', 'order__worker', 'order__service_ad')[:Receipt.KEEP_LAST]
    return render(request, 'customer/receipts.html', {
        'receipts': receipts,
        'keep_last': Receipt.KEEP_LAST,
    })


@customer_required
def reminders_list(request):
    """Mijozning AI eslatmalari va avto-eslatmalari."""
    items = Reminder.objects.filter(user=request.user).order_by(
        '-created_at'
    )[:50]
    return render(request, 'customer/reminders.html', {
        'reminders': items,
    })


@customer_required
def reminder_cancel(request, pk):
    """Kutilayotgan eslatmani bekor qilish."""
    if request.method == 'POST':
        rem = get_object_or_404(
            Reminder, pk=pk, user=request.user,
            status=Reminder.Status.PENDING,
        )
        rem.status = Reminder.Status.CANCELLED
        rem.save(update_fields=['status'])
        messages.info(request, "Eslatma bekor qilindi.")
    return redirect('customer:reminders_list')


@customer_required
def profile(request):
    if request.method == 'POST':
        user=request.user
        user.first_name=request.POST.get('first_name','').strip()
        user.last_name=request.POST.get('last_name','').strip()
        user.phone=request.POST.get('phone','').strip()
        if request.FILES.get('avatar'): user.avatar=request.FILES['avatar']
        user.save()
        messages.success(request, "Profil yangilandi!")
        return redirect('customer:profile')
    return render(request, 'customer/profile.html')
