# Waqt Owner Operations & Smart Restaurant Management

This document details the architecture, algorithms, and technical implementation of the Waqt Owner-side suite.

## 1. Concurrency & Allocation (Algorithm 1)
To prevent the classic double-booking race condition during busy periods, table allocation uses Django's transaction architecture coupled with database row-locking.

```python
@transaction.atomic
def greedy_allocate_table(restaurant, party_size):
    table = RestaurantTable.objects.select_for_update(skip_locked=True).filter(...)
    ...
```
When an owner clicks "Check-in" on a reservation, or "Seat" on a queue entry, the backend executes a single atomic block that securely locks the smallest suitable table, avoiding fragmentation.

## 2. Queue Eligibility (Algorithm 2)
The strict FIFO problem is solved by assessing table eligibility inline. When a Table of capacity `C` frees up, the backend queries the queue chronologically (`joined_at ASC`) and selects the first `QueueEntry` where `party_size <= C`. This allows a waiting party of 2 to skip a waiting party of 8 if only a 4-seater is available, maximizing floor efficiency without punishing smaller groups.

## 3. Wait Prediction & MAE (Algorithm 3)
Wait times are not arbitrary. The platform logs true `TableTurnover` cycles categorized into Party Buckets (`1-2`, `3-4`, `5-6`, `7+`).

When a customer joins the queue, their estimated wait is:
`(Parties Ahead / Compatible Tables Count) * Bucket Moving Average`

### Mean Absolute Error (MAE)
The Analytics dashboard provides owners with the exact accuracy score of these predictions by calculating the difference between the estimated wait and the *actual* duration from `joined_at` to `seated_at`.

## 4. Polling Architecture
In lieu of complex WebSocket infrastructure, Waqt utilizes an elegant `fetch()` + `setInterval()` cycle running every 12 seconds on the Dashboard and KDS.
To conserve battery and bandwidth, polling is instantly paused when `document.visibilityState` changes to hidden.

## 5. Live Kitchen Display System (KDS)
The KDS creates a pure pipeline for back-of-house operations:
1. `NEW`: Awaiting kitchen fire.
2. `PREPARING`: Currently cooking.
3. `READY`: Awaiting runner pickup.
4. `COMPLETED`: Cleared from the board.

This integrates natively into the central owner dashboard metrics.
