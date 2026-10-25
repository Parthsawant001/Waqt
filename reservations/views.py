from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import Reservation
from .forms import ReservationBookingForm
from restaurants.models import Restaurant, RestaurantTable
from queue_system.models import TableTurnover
from core.services.allocation_service import greedy_allocate_table

@login_required
def book_table_view(request, slug):
    """
    Table Reservation Flow:
    1. Customer picks date, time, party size.
    2. Greedy Allocation Algorithm finds smallest suitable available table.
    3. If found -> Confirmed. Table is assigned.
    4. If none found -> Clearly explain and offer 'Join Live Queue'.
    """
    restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)

    if not restaurant.is_connected_to_waqt():
        messages.error(
            request,
            f"'{restaurant.name}' is a public directory listing and is not currently connected to the Waqt live network. Table reservations are unavailable."
        )
        return redirect('restaurants:detail', slug=slug)

    if request.method == 'POST':
        form = ReservationBookingForm(request.POST)
        if form.is_valid():
            party_size = form.cleaned_data['party_size']
            res_date = form.cleaned_data['reservation_date']
            res_time = form.cleaned_data['reservation_time']
            special_req = form.cleaned_data.get('special_requests', '')

            # Execute transactional greedy allocation
            with transaction.atomic():
                table = greedy_allocate_table(restaurant, party_size)
                if table:
                    # Mark table RESERVED
                    table.status = 'RESERVED'
                    table.save(update_fields=['status'])

                    reservation = Reservation.objects.create(
                        customer=request.user,
                        restaurant=restaurant,
                        table=table,
                        party_size=party_size,
                        reservation_date=res_date,
                        reservation_time=res_time,
                        status='CONFIRMED',
                        special_requests=special_req
                    )
                    messages.success(
                        request,
                        f"Your table is confirmed! Assigned Table #{table.table_number} (Capacity: {table.capacity}) using Greedy Allocation."
                    )
                    return redirect('reservations:detail', pk=reservation.pk)
                else:
                    # No table available right now
                    messages.warning(
                        request,
                        f"All tables matching party size {party_size} are currently booked or occupied. You can join the Live Queue below!"
                    )
                    return render(request, 'customer/reservation_form.html', {
                        'restaurant': restaurant,
                        'form': form,
                        'no_tables_available': True,
                        'party_size': party_size,
                    })
    else:
        initial_party = request.GET.get('party', 2)
        form = ReservationBookingForm(initial={'party_size': initial_party})

    return render(request, 'customer/reservation_form.html', {
        'restaurant': restaurant,
        'form': form,
        'no_tables_available': False,
    })


@login_required
def reservation_detail_view(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    # Check permissions: either customer or restaurant owner
    if reservation.customer != request.user and reservation.restaurant.owner != request.user:
        messages.error(request, "Unauthorized access to reservation.")
        return redirect('accounts:dashboard')

    return render(request, 'customer/reservation_detail.html', {'reservation': reservation})


@login_required
def cancel_reservation_view(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    if reservation.customer != request.user and reservation.restaurant.owner != request.user:
        messages.error(request, "Unauthorized.")
        return redirect('accounts:dashboard')

    if reservation.status in ['PENDING', 'CONFIRMED']:
        with transaction.atomic():
            if reservation.table and reservation.table.status == 'RESERVED':
                reservation.table.status = 'AVAILABLE'
                reservation.table.save(update_fields=['status'])
            reservation.status = 'CANCELLED'
            reservation.save(update_fields=['status'])
        messages.info(request, "Reservation has been cancelled.")
    else:
        messages.warning(request, f"Cannot cancel reservation with status: {reservation.get_status_display()}")

    if request.user.is_owner():
        return redirect('owner:reservations')
    return redirect('accounts:dashboard')


# --- OWNER RESERVATIONS MANAGEMENT ---

@login_required
def owner_reservation_management_view(request):
    if not request.user.is_owner():
        messages.error(request, "Access restricted to restaurant owners.")
        return redirect('accounts:dashboard')

    restaurant = Restaurant.objects.filter(owner=request.user).first()
    if not restaurant:
        return redirect('restaurants:search')

    if request.method == 'POST':
        res_id = request.POST.get('reservation_id')
        action = request.POST.get('action')
        reservation = get_object_or_404(Reservation, id=res_id, restaurant=restaurant)

        if action == 'check_in':
            reservation.status = 'CHECKED_IN'
            reservation.checked_in_at = timezone.now()
            reservation.save(update_fields=['status', 'checked_in_at'])
            messages.success(request, f"Reservation #{reservation.id} marked as Checked-in.")
        elif action == 'seat':
            with transaction.atomic():
                reservation.status = 'CHECKED_IN'
                reservation.checked_in_at = timezone.now()
                if reservation.table:
                    reservation.table.status = 'OCCUPIED'
                    reservation.table.save(update_fields=['status'])
                reservation.save(update_fields=['status', 'checked_in_at'])
            messages.success(request, f"Party seated at Table #{reservation.table.table_number}.")
        elif action == 'complete':
            with transaction.atomic():
                now = timezone.now()
                reservation.status = 'COMPLETED'
                reservation.completed_at = now
                reservation.save(update_fields=['status', 'completed_at'])

                # Log actual TableTurnover for Algorithm 3 and MAE calculation
                if reservation.table:
                    start_time = reservation.checked_in_at or (now - timezone.timedelta(minutes=45))
                    duration = max(5.0, (now - start_time).total_seconds() / 60.0)
                    TableTurnover.objects.create(
                        restaurant=restaurant,
                        table=reservation.table,
                        reservation=reservation,
                        party_size=reservation.party_size,
                        occupied_at=start_time,
                        freed_at=now,
                        duration_minutes=round(duration, 1)
                    )
                    reservation.table.status = 'CLEANING'
                    reservation.table.save(update_fields=['status'])
            messages.success(request, f"Dining completed! Table #{reservation.table.table_number} marked for Cleaning. Turnover duration logged.")
        elif action == 'no_show':
            with transaction.atomic():
                reservation.status = 'NO_SHOW'
                if reservation.table and reservation.table.status == 'RESERVED':
                    reservation.table.status = 'AVAILABLE'
                    reservation.table.save(update_fields=['status'])
                reservation.save(update_fields=['status'])
            messages.info(request, f"Reservation #{reservation.id} marked as No Show.")

        return redirect('owner:reservations')

    reservations = restaurant.reservations.all().select_related('customer', 'table').order_by('-reservation_date', '-reservation_time')
    return render(request, 'owner/reservation_management.html', {
        'restaurant': restaurant,
        'reservations': reservations,
    })
