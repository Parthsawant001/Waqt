from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomerRegistrationForm, OwnerRegistrationForm, LoginForm
from reservations.models import Reservation
from queue_system.models import QueueEntry
from restaurants.models import Restaurant

def customer_register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Waqt, {user.first_name}! You can now reserve coastal tables and join live queues.")
            return redirect('accounts:dashboard')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'auth/customer_register.html', {'form': form})


def owner_register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    if request.method == 'POST':
        form = OwnerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome {user.first_name}! Your restaurant profile has been created.")
            return redirect('accounts:dashboard')
    else:
        form = OwnerRegistrationForm()
    return render(request, 'auth/owner_register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('accounts:dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have safely signed out.")
    return redirect('index')


@login_required
def dashboard_router_view(request):
    """
    Directs CUSTOMER to customer dashboard, and OWNER to owner dashboard.
    """
    if request.user.is_owner():
        return redirect('owner_dashboard')
    return redirect('customer_dashboard')


@login_required
def customer_dashboard_view(request):
    user = request.user
    active_reservations = Reservation.objects.filter(
        customer=user,
        status__in=['PENDING', 'CONFIRMED']
    ).select_related('restaurant', 'table')

    past_reservations = Reservation.objects.filter(
        customer=user,
        status__in=['CHECKED_IN', 'COMPLETED', 'CANCELLED', 'NO_SHOW']
    ).select_related('restaurant', 'table')[:10]

    active_queues = QueueEntry.objects.filter(
        customer=user,
        status__in=['WAITING', 'CALLED']
    ).select_related('restaurant')

    past_queues = QueueEntry.objects.filter(
        customer=user,
        status__in=['SEATED', 'COMPLETED', 'CANCELLED', 'EXPIRED']
    ).select_related('restaurant')[:10]

    nearby_restaurants = Restaurant.objects.filter(is_active=True)[:4]

    context = {
        'active_reservations': active_reservations,
        'past_reservations': past_reservations,
        'active_queues': active_queues,
        'past_queues': past_queues,
        'nearby_restaurants': nearby_restaurants,
    }
    return render(request, 'customer/dashboard.html', context)
