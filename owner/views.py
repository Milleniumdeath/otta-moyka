from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User
from core.models import Order, Bonus, LoyaltyToken
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import PriceList
from .forms import PriceListForm
from functools import wraps

def owner_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_owner:
            messages.error(request, "Ruxsat yo'q.")
            return redirect('accounts:role_redirect')
        return view_func(request, *args, **kwargs)
    return wrapper

@owner_required
def pricelist_view(request):
    """Narx ro'yxatini ko'rish va boshqarish"""
    pricelists = PriceList.objects.all().order_by('service_type')
    context = {'pricelists': pricelists}
    return render(request, 'owner/pricelist.html', context)


@owner_required
def pricelist_create(request):
    """Yangi narx qo'shish yoki yangilash"""
    if request.method == 'POST':
        form = PriceListForm(request.POST)
        if form.is_valid():
            # Agar bu xizmat turi uchun allaqachon narx bor bo'lsa, yangilash
            service_type = form.cleaned_data['service_type']
            pricelist, created = PriceList.objects.update_or_create(
                service_type=service_type,
                defaults={
                    'min_price':         form.cleaned_data['min_price'],
                    'max_price':         form.cleaned_data['max_price'],
                    'recommended_price': form.cleaned_data.get('recommended_price'),
                    'description':       form.cleaned_data.get('description', ''),
                    'is_active':         form.cleaned_data['is_active'],
                }
            )
            action = "yaratildi" if created else "yangilandi"
            messages.success(request, f"Narx ro'yxati {action}!")
            return redirect('owner:pricelist')
    else:
        form = PriceListForm()
    return render(request, 'owner/pricelist_form.html', {'form': form})


@owner_required
def pricelist_delete(request, pk):
    """Narxni o'chirish"""
    pricelist = get_object_or_404(PriceList, pk=pk)
    if request.method == 'POST':
        pricelist.delete()
        messages.success(request, "Narx o'chirildi!")
    return redirect('owner:pricelist')





# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────
@owner_required
def dashboard(request):
    completed = Order.objects.filter(status=Order.Status.COMPLETED).count()
    rejected  = Order.objects.filter(status=Order.Status.REJECTED).count()
    workers   = User.objects.filter(role=User.Role.WORKER, is_approved=True)
    pending   = User.objects.filter(role=User.Role.WORKER, is_approved=False)
    customers = User.objects.filter(role=User.Role.CUSTOMER)
    recent    = Order.objects.select_related(
        'customer', 'worker', 'car', 'service_ad'
    ).order_by('-created_at')[:10]

    return render(request, 'owner/dashboard.html', {
        'completed_orders': completed,
        'rejected_orders':  rejected,
        'workers_count':    workers.count(),
        'pending_count':    pending.count(),
        'customers_count':  customers.count(),
        'recent_orders':    recent,
    })


# ─────────────────────────────────────────────────────────────
# WORKERS
# ─────────────────────────────────────────────────────────────
@owner_required
def workers(request):
    from django.db.models import Avg, Count, F

    pending  = User.objects.filter(role=User.Role.WORKER, is_approved=False)
    approved = User.objects.filter(
        role=User.Role.WORKER, is_approved=True
    ).annotate(
        avg_rating=Avg('worker_orders__review__rating'),
        review_count=Count('worker_orders__review', distinct=True),
    ).order_by(F('avg_rating').desc(nulls_last=True))

    # Past reytingli ishchilar (kamida 3 ta baho, o'rtacha < 3.0) — nazorat uchun
    low_rated = [
        w for w in approved
        if w.review_count >= 3 and w.avg_rating is not None and w.avg_rating < 3.0
    ]

    return render(request, 'owner/workers.html', {
        'pending_workers':  pending,
        'approved_workers': approved,
        'pending_count':    pending.count(),
        'low_rated':        low_rated,
        'low_rated_count':  len(low_rated),
    })


@owner_required
def approve_worker(request, pk):
    if request.method == 'POST':
        worker = get_object_or_404(User, pk=pk, role=User.Role.WORKER)
        worker.is_approved = True
        worker.save()
        messages.success(request, f"{worker.get_full_name()} tasdiqlandi!")
    return redirect('owner:workers')


@owner_required
def delete_worker(request, pk):
    if request.method == 'POST':
        worker = get_object_or_404(User, pk=pk, role=User.Role.WORKER)
        worker.delete()
        messages.success(request, "Ishchi o'chirildi.")
    return redirect('owner:workers')


# ─────────────────────────────────────────────────────────────
# CUSTOMERS
# ─────────────────────────────────────────────────────────────
@owner_required
def customers(request):
    customers_list = User.objects.filter(
        role=User.Role.CUSTOMER
    ).prefetch_related('loyalty')
    return render(request, 'owner/customers.html', {'customers': customers_list})


@owner_required
def delete_customer(request, pk):
    if request.method == 'POST':
        customer = get_object_or_404(User, pk=pk, role=User.Role.CUSTOMER)
        customer.delete()
        messages.success(request, "Mijoz o'chirildi.")
    return redirect('owner:customers')


# ─────────────────────────────────────────────────────────────
# BONUSES
# ─────────────────────────────────────────────────────────────
@owner_required
def bonuses(request):
    bonuses_list = Bonus.objects.all().order_by('token_cost')
    return render(request, 'owner/bonuses.html', {'bonuses': bonuses_list})


@owner_required
def create_bonus(request):
    if request.method == 'POST':
        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        token_cost  = request.POST.get('token_cost', 0)
        quantity    = request.POST.get('quantity', 1)
        image       = request.FILES.get('image')
        if not name or not token_cost:
            messages.error(request, "Nom va narxni kiriting.")
            return redirect('owner:bonuses')
        Bonus.objects.create(
            name=name, description=description,
            token_cost=int(token_cost),
            quantity=int(quantity),
            image=image,
        )
        messages.success(request, f"'{name}' bonusi yaratildi!")
    return redirect('owner:bonuses')


@owner_required
def edit_bonus(request, pk):
    bonus = get_object_or_404(Bonus, pk=pk)
    if request.method == 'POST':
        bonus.name        = request.POST.get('name', bonus.name).strip()
        bonus.description = request.POST.get('description', bonus.description).strip()
        bonus.token_cost  = int(request.POST.get('token_cost', bonus.token_cost))
        bonus.quantity    = int(request.POST.get('quantity', bonus.quantity))
        if request.FILES.get('image'):
            bonus.image = request.FILES['image']
        bonus.save()
        messages.success(request, "Bonus yangilandi!")
        return redirect('owner:bonuses')
    return render(request, 'owner/bonus_edit.html', {'bonus': bonus})


@owner_required
def delete_bonus(request, pk):
    if request.method == 'POST':
        bonus = get_object_or_404(Bonus, pk=pk)
        bonus.delete()
        messages.success(request, "Bonus o'chirildi.")
    return redirect('owner:bonuses')


# ─────────────────────────────────────────────────────────────
# CAMERAS
# ─────────────────────────────────────────────────────────────
@owner_required
def cameras(request):
    return render(request, 'owner/cameras.html')


# ─────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────
@owner_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name  = request.POST.get('last_name', '').strip()
        user.phone      = request.POST.get('phone', '').strip()
        if request.FILES.get('avatar'):
            user.avatar = request.FILES['avatar']
        user.save()
        messages.success(request, "Profil yangilandi!")
        return redirect('owner:profile')
    return render(request, 'owner/profile.html')



