from django.db.models import Sum
from core.models import Order, Bonus, LoyaltyToken, Review
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
    from django.db.models import Avg, Count, F
    ads = ServiceAd.objects.filter(is_active=True).select_related('worker').annotate(
        worker_avg=Avg('worker__worker_orders__review__rating'),
        worker_reviews=Count('worker__worker_orders__review', distinct=True),
    ).order_by(F('worker_avg').desc(nulls_last=True), '-created_at')

    if selected_car:
        if selected_car.car_type == 'heavy':
            # Yuk mashina faqat "heavy" e'lonlarni ko'radi
            ads = ads.filter(service_type='heavy')
        else:
            # Yengil mashina "heavy" e'lonlarni ko'rmaydi
            ads = ads.exclude(service_type='heavy')

    context = {
        'cars':         cars,
        'selected_car': selected_car,
        'ads':          ads,
    }
    return render(request, 'customer/orders.html', context)


@customer_required
def book_order(request, ad_pk):
    if request.method == 'POST':
        ad     = get_object_or_404(ServiceAd, pk=ad_pk, is_active=True)
        car_id = request.POST.get('car_id')
        note   = request.POST.get('note', '').strip()
        scheduled = request.POST.get('scheduled_time')  # Qo‘shildi

        if not car_id:
            messages.error(request, "Mashina tanlang.")
            return redirect('customer:orders')

        car = get_object_or_404(Car, pk=car_id, owner=request.user)

        # ✅ Mashina turiga moslik tekshiruvi
        if ad.service_type == 'heavy' and car.car_type != 'heavy':
            messages.error(request, "Bu e'lon faqat yuk mashinalar uchun!")
            return redirect('customer:orders')
        if ad.service_type != 'heavy' and car.car_type == 'heavy':
            messages.error(request, "Yuk mashina uchun faqat 'Yuk transport' e'lonlaridan buyurtma bering!")
            return redirect('customer:orders')

        # ✅ Ish vaqti tekshiruvi (agar vaqt berilgan bo‘lsa)
        if scheduled:
            from datetime import datetime
            scheduled_dt = datetime.fromisoformat(scheduled)
            weekday = scheduled_dt.weekday()
            schedule = WorkSchedule.objects.filter(
                worker=ad.worker,
                weekday=weekday,
                is_active=True
            ).first()
            if not schedule:
                messages.warning(request, "Ishchi bu kuni ishlamaydi. Boshqa kun tanlang.")
                return redirect('customer:orders')
            if not (schedule.start_time <= scheduled_dt.time() <= schedule.end_time):
                messages.warning(request,
                    f"Ishchi bu kuni {schedule.start_time.strftime('%H:%M')}–"
                    f"{schedule.end_time.strftime('%H:%M')} oralig'ida ishlaydi.")
                return redirect('customer:orders')

        order = Order.objects.create(
            customer=request.user,
            worker=ad.worker,
            car=car,
            service_ad=ad,
            note=note,
            total_price=ad.price,
            status=Order.Status.PENDING,
            scheduled_time=scheduled,   # ✅ saqlash
        )

        # ✅ Agar zudlik bilan bo‘lsa, e'lonni nofaol qilish
        if not scheduled:
            ad.is_active = False
            ad.save()

        messages.success(request, "Buyurtma berildi! Ishchi tasdiqlashini kuting.")
    return redirect('customer:order_history')


@customer_required
def order_history(request):
    orders_list = Order.objects.filter(customer=request.user).select_related(
        'worker','car','service_ad'
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
