from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
import random

from accounts.models import User, EmailVerificationCode


def role_redirect(request):
    user = request.user
    if not user.is_authenticated:
        return redirect('accounts:login')
    if user.is_superuser or user.role == 'owner':
        return redirect('owner:dashboard')
    elif user.role == 'worker':
        if not user.is_approved:
            return redirect('accounts:pending_approval')
        return redirect('worker:dashboard')
    elif user.role == 'customer':
        return redirect('customer:dashboard')
    return redirect('accounts:login')


def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password1', '')
        confirm  = request.POST.get('password2', '')
        role     = request.POST.get('role', 'customer')

        if not email or not password:
            messages.error(request, "Email va parolni kiriting.")
            return render(request, 'accounts/register.html')

        if password != confirm:
            messages.error(request, "Parollar mos kelmadi.")
            return render(request, 'accounts/register.html')

        if len(password) < 8:
            messages.error(request, "Parol kamida 8 ta belgidan iborat bo'lishi kerak.")
            return render(request, 'accounts/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Bu email allaqachon ro'yxatdan o'tgan.")
            return render(request, 'accounts/register.html')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            role=role,
        )

        # Email tasdiqlash kodi
        code = str(random.randint(100000, 999999))
        EmailVerificationCode.objects.create(user=user, code=code)
        try:
            send_mail(
                subject="OTTA — Email tasdiqlash kodi",
                message=f"Tasdiqlash kodingiz: {code}\n\nKod 10 daqiqa amal qiladi.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except Exception:
            pass

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('accounts:verify_email')

    return render(request, 'accounts/register.html')


@login_required
def verify_email(request):
    user = request.user
    if user.email_verified:
        return redirect('accounts:role_redirect')

    if request.method == 'POST':
        entered = ''.join([
            request.POST.get(f'code_{i}', '') for i in range(1, 7)
        ]).strip()

        try:
            vc = EmailVerificationCode.objects.filter(
                user=user, code=entered
            ).latest('created_at')

            if vc.is_expired():
                messages.error(request, "Kod muddati o'tdi. Yangi kod so'rang.")
            else:
                user.email_verified = True
                user.save()
                vc.delete()
                # Ishchi bo'lsa → qo'shimcha ma'lumot sahifasiga
                if user.role == 'worker':
                    return redirect('accounts:worker_register')
                return redirect('accounts:role_redirect')
        except EmailVerificationCode.DoesNotExist:
            messages.error(request, "Kod noto'g'ri. Qayta tekshiring.")

    return render(request, 'accounts/verify_email.html')


@login_required
def resend_code(request):
    user = request.user
    EmailVerificationCode.objects.filter(user=user).delete()
    code = str(random.randint(100000, 999999))
    EmailVerificationCode.objects.create(user=user, code=code)
    try:
        send_mail(
            subject="OTTA — Yangi tasdiqlash kodi",
            message=f"Yangi tasdiqlash kodingiz: {code}\n\nKod 10 daqiqa amal qiladi.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass
    messages.success(request, "Yangi kod yuborildi!")
    return redirect('accounts:verify_email')


@login_required
def worker_register(request):
    user = request.user
    if user.role != 'worker':
        return redirect('accounts:role_redirect')
    if user.is_approved:
        return redirect('worker:dashboard')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        phone      = request.POST.get('phone', '').strip()

        if not first_name or not phone:
            messages.error(request, "Ism va telefon raqamini kiriting.")
            return render(request, 'accounts/worker_register.html')

        user.first_name = first_name
        user.last_name  = last_name
        user.phone      = phone
        user.save()

        messages.success(request, "Ma'lumotlar saqlandi! Moyka egasi tasdiqlashini kuting.")
        return redirect('accounts:pending_approval')

    return render(request, 'accounts/worker_register.html')


@login_required
def pending_approval(request):
    user = request.user
    if user.role != 'worker':
        return redirect('accounts:role_redirect')
    if user.is_approved:
        return redirect('worker:dashboard')
    return render(request, 'accounts/pending_approval.html')


def user_login(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('accounts:role_redirect')
        else:
            messages.error(request, "Email yoki parol noto'g'ri.")

    return render(request, 'accounts/login.html')


def user_logout(request):
    if request.method == 'POST':
        logout(request)
        return redirect('accounts:login')
    return redirect('accounts:login')
