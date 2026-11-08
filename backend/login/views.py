from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.hashers import make_password
from .models import User


def register_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    if request.method == 'POST':
        fullname = request.POST.get('fullname', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        age = request.POST.get('age')
        place = request.POST.get('place', '').strip()

        try:
            age = int(age) if age else None
        except ValueError:
            age = None

        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        profile = request.FILES.get('profile')

        if password != confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'login/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'login/register.html')

        user = User(
            fullname=fullname,
            email=email,
            phone=phone,
            address=address,
            age=age,
            place=place,
            role='user',
            status='active',
        )
        if profile:
            user.profile = profile
        user.set_password(password)
        user.save()
        messages.success(request, 'Account created! You can now log in.')
        return redirect('login')
    return render(request, 'login/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            if user.is_superuser:
                return redirect('admin_dashboard')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'login/login.html')


def logout_view(request):
    auth_logout(request)
    return redirect('login')
