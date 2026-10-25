"""
Algorithm 4: Weighted Restaurant Comparison Algorithm
=====================================================
Never call this AI. It is a transparent, deterministic multi-criteria decision analysis (MCDA) model.

Evaluation Criteria (Normalized to [0.0, 1.0]):
----------------------------------------------
1. Rating Score (S_rating):
   S_rating = clamp(rating / 5.0, 0.0, 1.0)
   (Higher rating gives higher score)

2. Distance Score (S_distance):
   S_distance = 1.0 - min(1.0, distance_km / MAX_DISTANCE)
   (Closer restaurants score higher, where MAX_DISTANCE defaults to 35 km for Palghar-Virar belt)

3. Price Score (S_price):
   Price tier mapped to [1, 2, 3, 4] for [₹, ₹₹, ₹₹₹, ₹₹₹₹]
   S_price = 1.0 - ((tier - 1) / 3.0)
   (Budget-friendly options score higher when price weight is prioritized)

4. Wait Time Score (S_wait):
   S_wait = 1.0 - min(1.0, current_wait_minutes / MAX_WAIT)
   (Shorter waiting time scores higher, MAX_WAIT = 90 minutes)

Weight Normalization:
---------------------
User configures weights: W_r, W_d, W_p, W_w (e.g. from UI sliders).
Sum_W = W_r + W_d + W_p + W_w
Normalized Weights: w_i = W_i / Sum_W (ensures sum is exactly 1.0 or 100%)

Final Waqt Score:
-----------------
Waqt Score = round(100 * (w_r * S_r + w_d * S_d + w_p * S_p + w_w * S_w))
"""

from typing import Dict, Any, List
from core.services.geo_service import calculate_haversine_distance
from core.services.wait_time_service import estimate_queue_wait_minutes

PRICE_TIER_MAP = {
    '₹': 1,
    '₹₹': 2,
    '₹₹₹': 3,
    '₹₹₹₹': 4,
}

MAX_DISTANCE_KM = 35.0
MAX_WAIT_MINUTES = 90.0

def calculate_waqt_score(
    restaurant,
    customer_lat: float,
    customer_lon: float,
    weight_rating: float = 30.0,
    weight_distance: float = 25.0,
    weight_price: float = 20.0,
    weight_wait: float = 25.0,
) -> Dict[str, Any]:
    """
    Computes transparent multi-criteria Waqt Score (0 - 100) and factor breakdown.
    """
    # 1. Normalize weights to sum to 1.0
    raw_weights = [max(0.0, float(w)) for w in [weight_rating, weight_distance, weight_price, weight_wait]]
    sum_w = sum(raw_weights)
    if sum_w <= 0.0:
        norm_weights = [0.25, 0.25, 0.25, 0.25]
    else:
        norm_weights = [w / sum_w for w in raw_weights]

    w_r, w_d, w_p, w_w = norm_weights

    # 2. Rating Factor
    rating = float(restaurant.average_rating)
    s_rating = max(0.0, min(1.0, rating / 5.0))

    # 3. Distance Factor (Haversine)
    dist_km = calculate_haversine_distance(
        customer_lat, customer_lon,
        float(restaurant.latitude), float(restaurant.longitude)
    )
    s_distance = max(0.0, 1.0 - min(1.0, dist_km / MAX_DISTANCE_KM))

    # 4. Price Factor
    tier = PRICE_TIER_MAP.get(restaurant.price_range, 2)
    s_price = max(0.0, 1.0 - ((tier - 1) / 3.0))

    # 5. Wait Time Factor
    current_wait = estimate_queue_wait_minutes(restaurant, party_size=2)
    s_wait = max(0.0, 1.0 - min(1.0, float(current_wait) / MAX_WAIT_MINUTES))

    # Final Weighted Aggregate
    aggregate = (w_r * s_rating) + (w_d * s_distance) + (w_p * s_price) + (w_w * s_wait)
    final_score = int(round(aggregate * 100))

    return {
        'restaurant_id': restaurant.id,
        'restaurant_name': restaurant.name,
        'waqt_score': final_score,
        'distance_km': round(dist_km, 1),
        'current_wait_minutes': current_wait,
        'rating': rating,
        'price_range': restaurant.price_range,
        'breakdown': {
            'rating_score': round(s_rating * 100, 1),
            'rating_contribution': round(w_r * s_rating * 100, 1),
            'distance_score': round(s_distance * 100, 1),
            'distance_contribution': round(w_d * s_distance * 100, 1),
            'price_score': round(s_price * 100, 1),
            'price_contribution': round(w_p * s_price * 100, 1),
            'wait_score': round(s_wait * 100, 1),
            'wait_contribution': round(w_w * s_wait * 100, 1),
        },
        'weights_applied': {
            'rating_pct': round(w_r * 100, 1),
            'distance_pct': round(w_d * 100, 1),
            'price_pct': round(w_p * 100, 1),
            'wait_pct': round(w_w * 100, 1),
        }
    }


def rank_restaurants_weighted(
    restaurants,
    customer_lat: float,
    customer_lon: float,
    w_rating: float = 30.0,
    w_distance: float = 25.0,
    w_price: float = 20.0,
    w_wait: float = 25.0
) -> List[Dict[str, Any]]:
    """
    Ranks an iterable of restaurants by their computed Waqt Score in descending order.
    """
    results = []
    for r in restaurants:
        score_data = calculate_waqt_score(
            r, customer_lat, customer_lon,
            weight_rating=w_rating,
            weight_distance=w_distance,
            weight_price=w_price,
            weight_wait=w_wait
        )
        score_data['restaurant_obj'] = r
        results.append(score_data)

    results.sort(key=lambda x: x['waqt_score'], reverse=True)
    return results
