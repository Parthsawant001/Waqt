"""
Algorithm 2: FIFO Queue with Table Eligibility
==============================================
Problem:
In a live restaurant queue, strict First-In-First-Out (FIFO) can cause severe floor deadlock
if the head of the queue is a large party (e.g. party of 8) waiting for a banquet table,
while multiple 2-person tables become vacant.
Conversely, unconstrained priority queues alienate customers by arbitrarily skipping order.

FIFO-with-Eligibility Solution:
-------------------------------
When a table of capacity C becomes vacant:
1. Scan the active queue in strict chronological order of arrival (joined_at ASC).
2. Select the FIRST waiting party whose party_size <= C.
3. Call that customer, preserving FIFO fairness among compatible party sizes.
4. Recalculate queue positions for remaining waiting customers.

Pseudocode:
-----------
function find_next_eligible_party(restaurant_id, table):
    1. waiting_parties = Query QueueEntry where restaurant_id == restaurant_id
                         AND status == 'WAITING'
                         ORDER BY joined_at ASC
    2. for entry in waiting_parties:
           if entry.party_size <= table.capacity:
               return entry  // First eligible customer in FIFO order
    3. return None (No waiting customer fits this table)

Time Complexity:
----------------
O(Q) where Q is current waiting queue length. Since typical active queue Q < 100,
this scan is lightning-fast (< 1 ms).
"""

from typing import Optional, List
from django.utils import timezone
from django.db import transaction
from queue_system.models import QueueEntry
from restaurants.models import RestaurantTable

def find_next_eligible_party(restaurant, table: RestaurantTable) -> Optional[QueueEntry]:
    """
    Returns the first waiting customer in FIFO order who can be accommodated by `table`.
    """
    waiting_queue = QueueEntry.objects.filter(
        restaurant=restaurant,
        status='WAITING'
    ).order_by('joined_at')

    for entry in waiting_queue:
        if entry.party_size <= table.capacity:
            return entry
    return None


@transaction.atomic
def call_next_eligible_party(restaurant, table: RestaurantTable) -> Optional[QueueEntry]:
    """
    Selects the first eligible customer and marks them CALLED, setting called_at timestamp.
    """
    entry = find_next_eligible_party(restaurant, table)
    if entry:
        entry.status = 'CALLED'
        entry.called_at = timezone.now()
        entry.save(update_fields=['status', 'called_at'])
        recalculate_queue_positions(restaurant)
    return entry


def recalculate_queue_positions(restaurant) -> None:
    """
    Recomputes sequential 1-indexed positions for all WAITING parties in the queue.
    """
    waiting_parties = QueueEntry.objects.filter(
        restaurant=restaurant,
        status='WAITING'
    ).order_by('joined_at')

    for idx, entry in enumerate(waiting_parties, start=1):
        if entry.position != idx:
            entry.position = idx
            entry.save(update_fields=['position'])
