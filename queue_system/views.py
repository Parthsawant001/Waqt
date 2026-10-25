from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import QueueEntry, TableTurnover
from .forms import JoinQueueForm
from restaurants.models import Restaurant, RestaurantTable
from core.services.wait_time_service import estimate_queue_wait_minutes
from core.services.queue_service import (
    find_next_eligible_party,
    call_next_eligible_party,
    recalculate_queue_positions
)

@login_required
def join_queue_view(request, slug):
    restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)

    if not restaurant.is_connected_to_waqt():
        messages.error(
            request,
            f"'{restaurant.name}' is a public directory listing and is not connected to the Waqt live queue network."
        )
        return redirect('restaurants:detail', slug=slug)

    # Check if user already has an active queue ticket here
    existing = QueueEntry.objects.filter(
        customer=request.user,
        restaurant=restaurant,
        status__in=['WAITING', 'CALLED']
    ).first()

    if existing:
        messages.info(request, f"You already have an active queue ticket (#{existing.position}) at {restaurant.name}!")
        return redirect('queue_system:status', pk=existing.pk)

    if request.method == 'POST':
        form = JoinQueueForm(request.POST)
        if form.is_valid():
            party_size = form.cleaned_data['party_size']
            with transaction.atomic():
                # Count current waiting parties
                waiting_count = QueueEntry.objects.filter(
                    restaurant=restaurant,
                    status='WAITING'
                ).count()
                pos = waiting_count + 1
                wait_min = estimate_queue_wait_minutes(restaurant, party_size, queue_position=pos)

                ticket = QueueEntry.objects.create(
                    customer=request.user,
                    restaurant=restaurant,
                    party_size=party_size,
                    position=pos,
                    estimated_wait_minutes=wait_min,
                    status='WAITING'
                )

            messages.success(request, f"Joined the live queue! Your ticket number is #{ticket.position}.")
            return redirect('queue_system:status', pk=ticket.pk)
    else:
        party_size = int(request.GET.get('party', 2))
        form = JoinQueueForm(initial={'party_size': party_size})

    est_wait = estimate_queue_wait_minutes(restaurant, 2)
    waiting_parties = restaurant.waiting_queue_count()

    context = {
        'restaurant': restaurant,
        'form': form,
        'estimated_wait': est_wait,
        'waiting_parties': waiting_parties,
    }
    return render(request, 'customer/join_queue.html', context)


@login_required
def queue_status_view(request, pk):
    """
    Live Queue Tracker for Diners:
    - Real-time position (e.g. Queue #07)
    - Estimated wait minutes (calculated via Algorithm 3)
    - Parties ahead
    - Web Notification API trigger when status transitions to CALLED
    - Polled by vanilla JS every 10-15s
    """
    ticket = get_object_or_404(QueueEntry, pk=pk)

    # Check permissions
    if ticket.customer != request.user and ticket.restaurant.owner != request.user:
        messages.error(request, "Unauthorized access to queue ticket.")
        return redirect('accounts:dashboard')

    parties_ahead = max(0, ticket.position - 1) if ticket.status == 'WAITING' else 0

    context = {
        'ticket': ticket,
        'restaurant': ticket.restaurant,
        'parties_ahead': parties_ahead,
    }
    return render(request, 'customer/queue_status.html', context)


@login_required
def cancel_queue_view(request, pk):
    ticket = get_object_or_404(QueueEntry, pk=pk)
    if ticket.customer != request.user and ticket.restaurant.owner != request.user:
        messages.error(request, "Unauthorized.")
        return redirect('accounts:dashboard')

    if ticket.status in ['WAITING', 'CALLED']:
        ticket.status = 'CANCELLED'
        ticket.save(update_fields=['status'])
        recalculate_queue_positions(ticket.restaurant)
        messages.info(request, "Your queue ticket has been cancelled.")
    else:
        messages.warning(request, f"Cannot cancel ticket in status {ticket.get_status_display()}.")

    if request.user.is_owner():
        return redirect('owner:queue')
    return redirect('accounts:dashboard')


# --- OWNER QUEUE MANAGEMENT ---

@login_required
def owner_queue_management_view(request):
    if not request.user.is_owner():
        messages.error(request, "Access restricted to restaurant owners.")
        return redirect('accounts:dashboard')

    restaurant = Restaurant.objects.filter(owner=request.user).first()
    if not restaurant:
        return redirect('restaurants:search')

    available_tables = restaurant.tables.filter(status='AVAILABLE').order_by('capacity')
    waiting_queue = restaurant.queue_entries.filter(status='WAITING').order_by('joined_at')
    called_queue = restaurant.queue_entries.filter(status='CALLED').order_by('called_at')
    seated_queue = restaurant.queue_entries.filter(status='SEATED').order_by('-seated_at')[:8]

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'call_eligible':
            table_id = request.POST.get('table_id')
            table = get_object_or_404(RestaurantTable, id=table_id, restaurant=restaurant)
            called_entry = call_next_eligible_party(restaurant, table)
            if called_entry:
                messages.success(
                    request,
                    f"Called customer '{called_entry.customer.first_name or called_entry.customer.username}' (Party of {called_entry.party_size}) for Table {table.table_number} using FIFO with Table Eligibility!"
                )
            else:
                messages.warning(request, f"No waiting parties fit Table {table.table_number} (Capacity: {table.capacity}).")
            return redirect('owner:queue')

        elif action == 'seat':
            entry_id = request.POST.get('entry_id')
            table_id = request.POST.get('table_id')
            entry = get_object_or_404(QueueEntry, id=entry_id, restaurant=restaurant)
            table = get_object_or_404(RestaurantTable, id=table_id, restaurant=restaurant)

            with transaction.atomic():
                entry.status = 'SEATED'
                entry.seated_at = timezone.now()
                entry.save(update_fields=['status', 'seated_at'])

                table.status = 'OCCUPIED'
                table.save(update_fields=['status'])

                recalculate_queue_positions(restaurant)

            messages.success(request, f"Seated {entry.customer.username} at Table {table.table_number}.")
            return redirect('owner:queue')

        elif action == 'complete':
            entry_id = request.POST.get('entry_id')
            table_id = request.POST.get('table_id')
            entry = get_object_or_404(QueueEntry, id=entry_id, restaurant=restaurant)
            table = get_object_or_404(RestaurantTable, id=table_id, restaurant=restaurant)

            with transaction.atomic():
                now = timezone.now()
                entry.status = 'COMPLETED'
                entry.save(update_fields=['status'])

                duration = max(5.0, (now - (entry.seated_at or (now - timezone.timedelta(minutes=35)))).total_seconds() / 60.0)
                TableTurnover.objects.create(
                    restaurant=restaurant,
                    table=table,
                    party_size=entry.party_size,
                    occupied_at=entry.seated_at or (now - timezone.timedelta(minutes=35)),
                    freed_at=now,
                    duration_minutes=round(duration, 1)
                )

                table.status = 'CLEANING'
                table.save(update_fields=['status'])

            messages.success(request, f"Dining completed! Logged turnover of {duration:.1f} mins for Table {table.table_number}. Marked for Cleaning.")
            return redirect('owner:queue')

    context = {
        'restaurant': restaurant,
        'available_tables': available_tables,
        'waiting_queue': waiting_queue,
        'called_queue': called_queue,
        'seated_queue': seated_queue,
    }
    return render(request, 'owner/queue_management.html', context)
