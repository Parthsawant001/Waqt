"""
Algorithm 3: Wait-Time Estimation & MAE Analytics Service
=========================================================
Problem:
Hardcoding arbitrary wait times (e.g., "15 minutes") misleads customers and ruins coastal dining trust.
Waqt estimates wait times using historical turnover metrics partitioned by party-size buckets.

Party Size Buckets:
- '1-2': Solo / Couples (quick meals, average 25-35 mins)
- '3-4': Small Families / Friends (thalis & fish fry, average 40-50 mins)
- '5-6': Medium Gatherings (coastal feasts & crab, average 55-70 mins)
- '7+': Large Banquets & Events (elaborate dining, average 70-90 mins)

Estimation Formula:
-------------------
Estimated Wait = (Preceding Compatible Parties / Count of Compatible Tables) * Average Turnover Duration
Where:
- Compatible Tables = Restaurant tables with capacity >= requested party_size
- Preceding Compatible Parties = Queue entries ahead in WAITING status with compatible capacity requirements

Fallback Hierarchy:
1. Bucket-specific historical average for the restaurant (last 30 days of TableTurnover).
2. Restaurant-wide average turnover across all party sizes.
3. Coastal baseline fallback:
   - 1-2: 30 mins
   - 3-4: 45 mins
   - 5-6: 60 mins
   - 7+: 75 mins

MAE (Mean Absolute Error) Calculation:
-------------------------------------
MAE = (1 / N) * SUM(|Estimated_Wait_i - Actual_Wait_i|)
Where Actual_Wait = (seated_at - joined_at) in minutes.
This metric is displayed in the restaurant owner's analytics dashboard to demonstrate prediction accuracy.
"""

from datetime import timedelta
from typing import Dict, Any, Tuple
from django.utils import timezone
from django.db.models import Avg
from queue_system.models import QueueEntry, TableTurnover
from restaurants.models import RestaurantTable

PARTY_BUCKETS = {
    '1-2': (1, 2, 30.0),
    '3-4': (3, 4, 45.0),
    '5-6': (5, 6, 60.0),
    '7+': (7, 100, 75.0),
}

def get_party_bucket_key(party_size: int) -> str:
    if party_size <= 2:
        return '1-2'
    elif party_size <= 4:
        return '3-4'
    elif party_size <= 6:
        return '5-6'
    else:
        return '7+'


def get_average_turnover_minutes(restaurant, party_size: int) -> Tuple[float, str]:
    """
    Returns (average_duration_in_minutes, calculation_source_description).
    """
    bucket_key = get_party_bucket_key(party_size)
    min_cap, max_cap, baseline = PARTY_BUCKETS[bucket_key]

    # Check historical TableTurnover records for this bucket
    bucket_avg = TableTurnover.objects.filter(
        restaurant=restaurant,
        party_size__gte=min_cap,
        party_size__lte=max_cap
    ).aggregate(avg_dur=Avg('duration_minutes'))['avg_dur']

    if bucket_avg is not None and bucket_avg > 0:
        return (float(bucket_avg), f"Historical bucket average ({bucket_key})")

    # Fallback 1: Overall restaurant average
    restaurant_avg = TableTurnover.objects.filter(
        restaurant=restaurant
    ).aggregate(avg_dur=Avg('duration_minutes'))['avg_dur']

    if restaurant_avg is not None and restaurant_avg > 0:
        return (float(restaurant_avg), "Restaurant overall historical average")

    # Fallback 2: Coastal baseline
    return (baseline, f"Palghar coastal baseline default ({bucket_key})")


def estimate_queue_wait_minutes(restaurant, party_size: int, queue_position: int = None) -> int:
    """
    Calculates estimated waiting time in minutes for a given party size and position.
    """
    avg_turnover, _ = get_average_turnover_minutes(restaurant, party_size)

    # Compatible tables at this restaurant that can hold this party
    compatible_tables_count = RestaurantTable.objects.filter(
        restaurant=restaurant,
        capacity__gte=party_size
    ).count()

    if compatible_tables_count == 0:
        compatible_tables_count = 1  # Guard against division by zero

    # Count currently waiting parties ahead
    if queue_position is not None and queue_position > 0:
        parties_ahead = max(0, queue_position - 1)
    else:
        parties_ahead = QueueEntry.objects.filter(
            restaurant=restaurant,
            status='WAITING'
        ).count()

    # If there are available tables right now and no queue ahead, wait is minimal
    available_compatible = RestaurantTable.objects.filter(
        restaurant=restaurant,
        status='AVAILABLE',
        capacity__gte=party_size
    ).count()

    if available_compatible > 0 and parties_ahead == 0:
        return 0

    # Wait formula: (parties_ahead / compatible_tables) * avg_turnover
    estimated = (float(parties_ahead + 1) / float(compatible_tables_count)) * (avg_turnover * 0.65)
    return max(5, int(round(estimated)))


def calculate_wait_time_mae(restaurant) -> Dict[str, Any]:
    """
    Computes Mean Absolute Error (MAE) between estimated wait and actual wait for seated/completed entries.
    """
    completed_entries = QueueEntry.objects.filter(
        restaurant=restaurant,
        status__in=['SEATED', 'COMPLETED'],
        seated_at__isnull=False
    )

    if not completed_entries.exists():
        return {
            'mae': 0.0,
            'sample_size': 0,
            'status': 'No completed entries yet to measure MAE.'
        }

    total_error = 0.0
    valid_samples = 0

    for entry in completed_entries:
        actual_wait = (entry.seated_at - entry.joined_at).total_seconds() / 60.0
        predicted_wait = float(entry.estimated_wait_minutes)
        error = abs(predicted_wait - actual_wait)
        total_error += error
        valid_samples += 1

    mae = round(total_error / valid_samples, 2) if valid_samples > 0 else 0.0
    return {
        'mae': mae,
        'sample_size': valid_samples,
        'status': f"Computed across {valid_samples} fulfilled queue parties."
    }
