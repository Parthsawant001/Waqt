"""
Algorithm 5: Haversine Geolocation Distance Service
===================================================
Formula:
Given two points on Earth (lat1, lon1) and (lat2, lon2) in decimal degrees:
phi1, phi2 = radians(lat1), radians(lat2)
delta_phi = radians(lat2 - lat1)
delta_lambda = radians(lon2 - lon1)

a = sin^2(delta_phi / 2) + cos(phi1) * cos(phi2) * sin^2(delta_lambda / 2)
c = 2 * atan2(sqrt(a), sqrt(1 - a))
distance = R * c

Where:
R = 6371.0088 km (mean Earth radius)

Important Architectural Note:
Waqt uses Haversine distance for geographic straight-line proximity along the
Palghar–Virar coastal strip, not road-network routing.
"""

import math
from typing import Tuple

EARTH_RADIUS_KM = 6371.0088

# Reference coordinates for the Palghar-Virar coastal belt
PALGHAR_COASTAL_CENTER = (19.6936, 72.7655)
VIRAR_COASTAL_CENTER = (19.4700, 72.8000)

def calculate_haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """
    Computes great-circle distance between two coordinate pairs in kilometers.
    """
    try:
        lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    except (ValueError, TypeError):
        return 0.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    
    # Avoid numerical precision domain error for antipodal points
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    return round(EARTH_RADIUS_KM * c, 2)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Alias for calculate_haversine_distance."""
    return calculate_haversine_distance(lat1, lon1, lat2, lon2)


def get_default_coastal_coords() -> Tuple[float, float]:
    """
    Returns Palghar-Virar coastal anchor coordinate (Virar / Arnala beach area).
    """
    return (19.4632, 72.7845)
