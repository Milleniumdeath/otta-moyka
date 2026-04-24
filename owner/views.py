from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User
from core.models import Order, Bonus, LoyaltyToken



# ─────────────────────────────────────────────────────────────
# DECORATOR
# ─────────────────────────────────────────────────────────────
def owner_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_owner:
            messages.error(request, "Ruxsat yo'q.")
            return redirect('accounts:role_redirect')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


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
    pending  = User.objects.filter(role=User.Role.WORKER, is_approved=False)
    approved = User.objects.filter(role=User.Role.WORKER, is_approved=True)
    return render(request, 'owner/workers.html', {
        'pending_workers':  pending,
        'approved_workers': approved,
        'pending_count':    pending.count(),
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



