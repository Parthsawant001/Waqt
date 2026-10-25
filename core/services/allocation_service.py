"""
Algorithm 1: Greedy Table Allocation Service
============================================
Problem:
Given a reservation or queue seating request for a party of size P, allocate the best
available table at a restaurant that minimizes wasted capacity while ensuring fair
utilization of larger family/group tables.

Pseudocode:
-----------
function allocate_table(restaurant_id, party_size):
    1. Begin Database Transaction
    2. candidates = Query RestaurantTable (select_for_update skip_locked)
                    where restaurant_id == restaurant_id
                    AND status == 'AVAILABLE'
                    AND capacity >= party_size
                    ORDER BY capacity ASC, table_number ASC
    3. if candidates is empty:
           return None (No suitable table available)
    4. selected_table = candidates.first()
    5. Update selected_table status to OCCUPIED / RESERVED
    6. return selected_table

Time Complexity:
----------------
- Filtering & Query: O(N) where N is total tables at the restaurant.
- Sorting: O(N log N) handled efficiently by the SQL database engine.
- Concurrency: O(1) lock acquisition using select_for_update(skip_locked=True).
"""

from typing import Optional
from django.db import transaction
from restaurants.models import RestaurantTable

@transaction.atomic
def greedy_allocate_table(restaurant, party_size: int, mark_as: str = None) -> Optional[RestaurantTable]:
    """
    Atomically finds, locks, and allocates the optimal available table.
    Uses select_for_update(skip_locked=True) to prevent double booking.
    """
    if party_size <= 0:
        return None

    # Query best fit table directly in the DB using row-level locking
    table = RestaurantTable.objects.select_for_update(skip_locked=True).filter(
        restaurant=restaurant,
        status='AVAILABLE',
        capacity__gte=party_size
    ).order_by('capacity', 'table_number').first()

    if table and mark_as:
        table.status = mark_as
        table.save(update_fields=['status'])

    return table


@transaction.atomic
def reserve_table_greedily(restaurant, party_size: int, reservation=None) -> Optional[RestaurantTable]:
    """
    Allocates the best table and transitions its status to RESERVED.
    """
    table = greedy_allocate_table(restaurant, party_size, mark_as='RESERVED')
    if table and reservation:
        reservation.table = table
        reservation.status = 'CONFIRMED'
        reservation.save(update_fields=['table', 'status'])
    return table
