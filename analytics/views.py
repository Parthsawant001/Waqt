from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count
from restaurants.models import Restaurant
from queue_system.models import TableTurnover, QueueEntry
from core.services.wait_time_service import calculate_wait_time_mae, PARTY_BUCKETS

@login_required
def owner_analytics_view(request):
    if not request.user.is_owner():
        messages.error(request, "Access restricted to restaurant owners.")
        return redirect('accounts:dashboard')

    restaurant = Restaurant.objects.filter(owner=request.user).first()
    if not restaurant:
        return redirect('restaurants:search')

    # 1. Calculate MAE for wait time algorithm
    mae_report = calculate_wait_time_mae(restaurant)

    # 2. Historical turnover statistics partitioned by party bucket
    bucket_stats = []
    for key, (min_c, max_c, baseline) in PARTY_BUCKETS.items():
        qs = TableTurnover.objects.filter(
            restaurant=restaurant,
            party_size__gte=min_c,
            party_size__lte=max_c
        )
        avg_val = qs.aggregate(Avg('duration_minutes'))['duration_minutes__avg']
        count_val = qs.count()
        bucket_stats.append({
            'bucket': key,
            'label': f"Party {key}",
            'count': count_val,
            'avg_duration': round(float(avg_val), 1) if avg_val else baseline,
            'is_fallback': avg_val is None,
            'baseline': baseline
        })

    # 3. Overall table metrics
    total_turnovers = TableTurnover.objects.filter(restaurant=restaurant).count()
    overall_avg = TableTurnover.objects.filter(restaurant=restaurant).aggregate(Avg('duration_minutes'))['duration_minutes__avg']
    recent_turnovers = TableTurnover.objects.filter(restaurant=restaurant).select_related('table')[:15]

    context = {
        'restaurant': restaurant,
        'mae_report': mae_report,
        'bucket_stats': bucket_stats,
        'total_turnovers': total_turnovers,
        'overall_avg_duration': round(float(overall_avg), 1) if overall_avg else 45.0,
        'recent_turnovers': recent_turnovers,
    }
    return render(request, 'owner/analytics.html', context)
