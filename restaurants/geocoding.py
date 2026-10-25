"""
Nominatim Geocoding Integration Service
=======================================
Respects OpenStreetMap / Nominatim guidelines:
- Custom User-Agent identification
- Timeout and exception resilience
- Safe fallback to Palghar-Virar coastal defaults or user coordinates
- Never blocks registration if external network or geocoder is unavailable.
"""

import requests
import logging
from typing import Tuple, Optional
from django.conf import settings
from core.services.geo_service import PALGHAR_COASTAL_CENTER

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

def geocode_address(address: str, locality: str = "") -> Tuple[float, float, bool]:
    """
    Attempts to geocode an address in the Palghar-Virar coastal belt.
    Returns (latitude, longitude, was_successful).
    """
    user_agent = getattr(settings, 'NOMINATIM_USER_AGENT', 'WaqtCoastalPlatform/1.0')
    headers = {
        'User-Agent': user_agent,
        'Accept-Language': 'en'
    }

    query = f"{address}, {locality}, Palghar, Maharashtra, India" if locality else f"{address}, Maharashtra, India"

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                'q': query,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'in'
            },
            headers=headers,
            timeout=4.0
        )
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return (lat, lon, True)
    except Exception as e:
        logger.warning(f"Nominatim geocoding failed or timed out: {e}")

    # Fallback to standard coastal coordinates for Palghar/Virar area
    locality_lower = locality.lower() if locality else ""
    if "virar" in locality_lower or "arnala" in locality_lower:
        return (19.4632, 72.7845, False)
    elif "kelva" in locality_lower:
        return (19.6175, 72.7315, False)
    elif "satpati" in locality_lower:
        return (19.7345, 72.7050, False)
    elif "dahanu" in locality_lower:
        return (19.9720, 72.7300, False)
    elif "vasai" in locality_lower:
        return (19.3620, 72.8120, False)
    elif "shirgaon" in locality_lower:
        return (19.7020, 72.7210, False)

    return (PALGHAR_COASTAL_CENTER[0], PALGHAR_COASTAL_CENTER[1], False)
