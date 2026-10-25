"""
Management Command: import_restaurants
======================================
Imports verified public directory restaurants across the Palghar-Virar coastal belt
from JSON data files (data/restaurants/*.json).

Features:
- Validates coastal geographic bounds (19.0 - 20.6 N, 72.5 - 73.5 E)
- Smart duplicate detection using normalized name matching and Haversine proximity
- Preserves existing LIVE / DEMO restaurant statuses and owner claims
- Sets waqt_status='LISTED' and claim_status='UNCLAIMED' for new listings
"""

import json
import os
import re
from datetime import datetime, time
from difflib import SequenceMatcher
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from restaurants.models import Restaurant
from core.services.geo_service import haversine_distance


def normalize_restaurant_name(name: str) -> str:
    """Strip common prefixes, suffixes, and noise words for fuzzy matching."""
    s = name.lower()
    s = re.sub(r'[^\w\s]', ' ', s)
    noise_words = {'hotel', 'restaurant', 'dhaba', 'bar', 'family', 'pure', 'veg', 'non', 'cafe', 'caterers', 'restro', 'and', '&'}
    tokens = [w for w in s.split() if w not in noise_words]
    return ' '.join(tokens)


def string_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def parse_time_str(val):
    if not val:
        return None
    if isinstance(val, time):
        return val
    try:
        parts = str(val).strip().split(':')
        return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
    except Exception:
        return None


class Command(BaseCommand):
    help = "Imports verified real coastal restaurants from data/restaurants/ JSON files."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            type=str,
            default=None,
            help="Path to directory containing restaurant JSON files (default: data/restaurants)",
        )
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help="Path to a single JSON file to import",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Validate and check duplicates without modifying database",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING("--- RUNNING IN DRY RUN MODE (No DB Changes) ---"))

        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        target_dir = options['dir']
        target_file = options['file']

        files_to_process = []
        if target_file:
            fpath = Path(target_file)
            if not fpath.exists():
                raise CommandError(f"Specified file does not exist: {fpath}")
            files_to_process.append(fpath)
        else:
            search_dir = Path(target_dir) if target_dir else base_dir / 'data' / 'restaurants'
            if not search_dir.exists():
                raise CommandError(f"Directory does not exist: {search_dir}")
            files_to_process = sorted(list(search_dir.glob('*.json')))

        if not files_to_process:
            self.stdout.write(self.style.WARNING("No JSON files found to import."))
            return

        self.stdout.write(self.style.NOTICE(f"Found {len(files_to_process)} dataset file(s) to process."))

        # Coastal bounds: 19.0 <= lat <= 20.6, 72.5 <= lng <= 73.5
        MIN_LAT, MAX_LAT = 19.0, 20.6
        MIN_LNG, MAX_LNG = 72.5, 73.5

        existing_restaurants = list(Restaurant.objects.all())
        created_count = 0
        updated_count = 0
        skipped_invalid = 0

        for fpath in files_to_process:
            self.stdout.write(f"\nProcessing file: {fpath.name}")
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error reading {fpath.name}: {e}"))
                continue

            for item in entries:
                name = item.get('name', '').strip()
                if not name:
                    self.stdout.write(self.style.WARNING("  Skipping entry with missing name"))
                    skipped_invalid += 1
                    continue

                try:
                    lat = float(item.get('latitude'))
                    lng = float(item.get('longitude'))
                except (ValueError, TypeError):
                    self.stdout.write(self.style.WARNING(f"  Skipping '{name}': invalid coordinates"))
                    skipped_invalid += 1
                    continue

                if not (MIN_LAT <= lat <= MAX_LAT and MIN_LNG <= lng <= MAX_LNG):
                    self.stdout.write(self.style.WARNING(f"  Skipping '{name}': coordinates ({lat}, {lng}) outside coastal bounds"))
                    skipped_invalid += 1
                    continue

                locality = item.get('locality', '').strip()
                city = item.get('city') or locality or 'Palghar'
                district = item.get('district') or 'Palghar'
                cuisine_type = item.get('cuisine_type') or 'Coastal Seafood'
                description = item.get('description') or ''
                address = item.get('address') or ''
                price_range = item.get('price_range') or '₹₹'
                phone = item.get('phone') or ''
                opening_time = parse_time_str(item.get('opening_time')) or time(11, 0)
                closing_time = parse_time_str(item.get('closing_time')) or time(23, 0)
                external_rating = item.get('external_rating')
                external_rating_source = item.get('external_rating_source') or 'Public Directory'
                source_name = item.get('source_name') or 'Public Coastal Directory'
                source_url = item.get('source_url') or ''
                website = item.get('website') or ''

                # Duplicate detection
                norm_name = normalize_restaurant_name(name)
                matched_rest = None

                for ex in existing_restaurants:
                    ex_norm = normalize_restaurant_name(ex.name)
                    # Check 1: Exact normalized name match in same locality
                    if norm_name and ex_norm and norm_name == ex_norm and ex.locality.lower() == locality.lower():
                        matched_rest = ex
                        break
                    # Check 2: High name similarity + within 200m
                    if norm_name and ex_norm:
                        sim = string_similarity(norm_name, ex_norm)
                        if sim >= 0.8:
                            dist_km = haversine_distance(lat, lng, float(ex.latitude), float(ex.longitude))
                            if dist_km <= 0.2:  # 200 meters
                                matched_rest = ex
                                break

                if matched_rest:
                    # Update metadata without overwriting LIVE/DEMO status or verified claims
                    if not dry_run:
                        matched_rest.address = address or matched_rest.address
                        matched_rest.locality = locality or matched_rest.locality
                        matched_rest.city = city or matched_rest.city
                        matched_rest.district = district or matched_rest.district
                        matched_rest.cuisine_type = cuisine_type or matched_rest.cuisine_type
                        matched_rest.description = description or matched_rest.description
                        matched_rest.price_range = price_range or matched_rest.price_range
                        if phone:
                            matched_rest.phone = phone
                        if external_rating is not None:
                            matched_rest.external_rating = external_rating
                            matched_rest.external_rating_source = external_rating_source
                        if source_name:
                            matched_rest.source_name = source_name
                        if source_url:
                            matched_rest.source_url = source_url
                        if website:
                            matched_rest.website = website
                        matched_rest.is_verified = True
                        matched_rest.last_verified_at = timezone.now()
                        matched_rest.save()

                    self.stdout.write(self.style.SUCCESS(f"  [UPDATED] '{name}' (matches existing id={matched_rest.id}, waqt_status={matched_rest.waqt_status})"))
                    updated_count += 1
                else:
                    # Create new listed restaurant
                    # Generate unique slug
                    base_slug = slugify(name) or 'restaurant'
                    slug = base_slug
                    counter = 1
                    while Restaurant.objects.filter(slug=slug).exists():
                        slug = f"{base_slug}-{slugify(locality)}-{counter}" if locality else f"{base_slug}-{counter}"
                        counter += 1

                    if not dry_run:
                        new_r = Restaurant.objects.create(
                            name=name,
                            slug=slug,
                            cuisine_type=cuisine_type,
                            description=description,
                            address=address,
                            locality=locality,
                            city=city,
                            district=district,
                            latitude=lat,
                            longitude=lng,
                            price_range=price_range,
                            phone=phone,
                            opening_time=opening_time,
                            closing_time=closing_time,
                            is_active=True,
                            is_verified=True,
                            is_demo=False,
                            waqt_status='LISTED',
                            claim_status='UNCLAIMED',
                            owner=None,
                            external_rating=external_rating,
                            external_rating_source=external_rating_source,
                            source_name=source_name,
                            source_url=source_url,
                            website=website or None,
                            last_verified_at=timezone.now(),
                        )
                        existing_restaurants.append(new_r)

                    self.stdout.write(self.style.SUCCESS(f"  [CREATED] '{name}' ({locality}) -> waqt_status=LISTED"))
                    created_count += 1

        self.stdout.write(self.style.NOTICE("\n--- IMPORT SUMMARY ---"))
        self.stdout.write(f"Total files: {len(files_to_process)}")
        self.stdout.write(f"New restaurants created: {created_count}")
        self.stdout.write(f"Existing restaurants updated: {updated_count}")
        self.stdout.write(f"Skipped / invalid: {skipped_invalid}")
        self.stdout.write(f"Total in database now: {Restaurant.objects.count() if not dry_run else len(existing_restaurants)}")
