"""
Unit & Integration Tests for Waqt Core Algorithms
=================================================
Covers:
1. Algorithm 1: Greedy Table Allocation
2. Algorithm 2: FIFO Queue with Table Eligibility
3. Algorithm 3: Wait-Time Estimation & MAE Calculation
4. Algorithm 4: Weighted Restaurant Comparison
5. Algorithm 5: Haversine Geolocation Distance
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date, time
from accounts.models import User
from restaurants.models import Restaurant, RestaurantTable, MenuItem, RestaurantClaim
from queue_system.models import QueueEntry, TableTurnover
from reservations.models import Reservation
from core.services.allocation_service import greedy_allocate_table, reserve_table_greedily
from core.services.queue_service import find_next_eligible_party, call_next_eligible_party, recalculate_queue_positions
from core.services.wait_time_service import estimate_queue_wait_minutes, calculate_wait_time_mae, get_average_turnover_minutes
from core.services.comparison_service import calculate_waqt_score, rank_restaurants_weighted
from core.services.geo_service import calculate_haversine_distance

class AlgorithmTests(TestCase):
    def setUp(self):
        # Create Owner & Customer
        self.owner = User.objects.create_user(
            username='test_owner',
            password='Password@123',
            role='OWNER'
        )
        self.customer1 = User.objects.create_user(
            username='cust_one',
            password='Password@123',
            role='CUSTOMER'
        )
        self.customer2 = User.objects.create_user(
            username='cust_two',
            password='Password@123',
            role='CUSTOMER'
        )
        self.customer3 = User.objects.create_user(
            username='cust_three',
            password='Password@123',
            role='CUSTOMER'
        )

        # Create Restaurant in Satpati, Palghar
        self.restaurant = Restaurant.objects.create(
            owner=self.owner,
            name='Test Satpati Koli Kitchen',
            description='Fresh catch right by the jetty',
            cuisine_type='Koli Seafood',
            address='Jetty Road',
            locality='Satpati',
            latitude=19.7345,
            longitude=72.7050,
            price_range='₹₹',
            phone='9823000000',
            average_rating=4.8
        )

        # Create Tables with different capacities
        # Table 1: cap 2, AVAILABLE
        # Table 2: cap 4, AVAILABLE
        # Table 3: cap 6, AVAILABLE
        # Table 4: cap 8, AVAILABLE
        # Table 5: cap 4, AVAILABLE (tie breaker test)
        self.t1 = RestaurantTable.objects.create(restaurant=self.restaurant, table_number='1', capacity=2, status='AVAILABLE')
        self.t2 = RestaurantTable.objects.create(restaurant=self.restaurant, table_number='2', capacity=4, status='AVAILABLE')
        self.t3 = RestaurantTable.objects.create(restaurant=self.restaurant, table_number='3', capacity=6, status='AVAILABLE')
        self.t4 = RestaurantTable.objects.create(restaurant=self.restaurant, table_number='4', capacity=8, status='AVAILABLE')
        self.t5 = RestaurantTable.objects.create(restaurant=self.restaurant, table_number='5', capacity=4, status='AVAILABLE')

    def test_algorithm_1_greedy_table_allocation(self):
        """
        Verify Greedy Allocation:
        - Party of 3 selects Table 2 (smallest available capacity that fits, cap 4 vs cap 2,6,8).
        - Tie-breaking: Between Table 2 and Table 5 (both cap 4), chooses Table 2 (lower table number).
        - Prevents wasting Table 4 (cap 8).
        """
        # Party size 3
        selected = greedy_allocate_table(self.restaurant, party_size=3)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.table_number, '2')
        self.assertEqual(selected.capacity, 4)

        # Party size 1 -> selects Table 1 (cap 2)
        selected_solo = greedy_allocate_table(self.restaurant, party_size=1)
        self.assertEqual(selected_solo.table_number, '1')

        # Party size 7 -> selects Table 4 (cap 8)
        selected_large = greedy_allocate_table(self.restaurant, party_size=7)
        self.assertEqual(selected_large.table_number, '4')

        # Party size 10 (exceeds all tables) -> returns None
        selected_huge = greedy_allocate_table(self.restaurant, party_size=10)
        self.assertIsNone(selected_huge)

    def test_algorithm_2_fifo_with_table_eligibility(self):
        """
        Verify FIFO with eligibility:
        Queue:
        - Pos 1: cust_one (party 6)
        - Pos 2: cust_two (party 2)
        - Pos 3: cust_three (party 4)
        When a 2-person table frees up, Pos 2 (cust_two) should be selected.
        """
        now = timezone.now()
        q1 = QueueEntry.objects.create(
            customer=self.customer1,
            restaurant=self.restaurant,
            party_size=6,
            position=1,
            status='WAITING',
            joined_at=now - timedelta(minutes=20)
        )
        q2 = QueueEntry.objects.create(
            customer=self.customer2,
            restaurant=self.restaurant,
            party_size=2,
            position=2,
            status='WAITING',
            joined_at=now - timedelta(minutes=15)
        )
        q3 = QueueEntry.objects.create(
            customer=self.customer3,
            restaurant=self.restaurant,
            party_size=4,
            position=3,
            status='WAITING',
            joined_at=now - timedelta(minutes=10)
        )

        # 2-person table becomes ready
        small_table = self.t1  # capacity 2
        eligible = find_next_eligible_party(self.restaurant, small_table)
        self.assertIsNotNone(eligible)
        self.assertEqual(eligible.customer, self.customer2)
        self.assertEqual(eligible.party_size, 2)

        # Calling customer transitions them to CALLED and recalculates remaining positions
        called = call_next_eligible_party(self.restaurant, small_table)
        self.assertEqual(called.id, q2.id)
        self.assertEqual(called.status, 'CALLED')

        q1.refresh_from_db()
        q3.refresh_from_db()
        self.assertEqual(q1.position, 1)
        self.assertEqual(q3.position, 2)

    def test_algorithm_3_wait_time_and_mae(self):
        """
        Verify Turnover-based wait time estimation and MAE calculation:
        - Logs sample historical turnover durations.
        - Checks moving average lookup.
        - Checks MAE computation.
        """
        now = timezone.now()
        # Seed turnovers for party size 2
        TableTurnover.objects.create(
            restaurant=self.restaurant,
            table=self.t1,
            party_size=2,
            occupied_at=now - timedelta(days=1),
            freed_at=now - timedelta(days=1) + timedelta(minutes=30),
            duration_minutes=30.0
        )
        TableTurnover.objects.create(
            restaurant=self.restaurant,
            table=self.t1,
            party_size=2,
            occupied_at=now - timedelta(days=2),
            freed_at=now - timedelta(days=2) + timedelta(minutes=26),
            duration_minutes=26.0
        )

        avg_dur, src = get_average_turnover_minutes(self.restaurant, party_size=2)
        self.assertEqual(avg_dur, 28.0)
        self.assertIn("Historical bucket average", src)

        # Simulate 2 completed queue entries with known predictions
        # Entry A: estimated 20m, actual (seated - joined) 22m -> error 2m
        # Entry B: estimated 15m, actual 12m -> error 3m
        # Expected MAE = (2 + 3) / 2 = 2.5m
        QueueEntry.objects.create(
            customer=self.customer1,
            restaurant=self.restaurant,
            party_size=2,
            position=0,
            estimated_wait_minutes=20,
            status='SEATED',
            joined_at=now - timedelta(minutes=40),
            seated_at=now - timedelta(minutes=18)
        )
        QueueEntry.objects.create(
            customer=self.customer2,
            restaurant=self.restaurant,
            party_size=2,
            position=0,
            estimated_wait_minutes=15,
            status='SEATED',
            joined_at=now - timedelta(minutes=30),
            seated_at=now - timedelta(minutes=18)
        )

        mae_report = calculate_wait_time_mae(self.restaurant)
        self.assertEqual(mae_report['sample_size'], 2)
        self.assertAlmostEqual(mae_report['mae'], 2.5, places=1)

    def test_algorithm_4_weighted_restaurant_comparison(self):
        """
        Verify Weighted Comparison Algorithm:
        - Sliders normalize to 100%.
        - Output score is between 0 and 100.
        - Provides detailed contribution breakdowns.
        """
        cust_lat, cust_lon = 19.4632, 72.7845  # Near Arnala / Virar
        score_data = calculate_waqt_score(
            self.restaurant,
            customer_lat=cust_lat,
            customer_lon=cust_lon,
            weight_rating=40,
            weight_distance=30,
            weight_price=15,
            weight_wait=15
        )

        self.assertIn('waqt_score', score_data)
        self.assertTrue(0 <= score_data['waqt_score'] <= 100)
        self.assertIn('breakdown', score_data)
        self.assertIn('weights_applied', score_data)
        # Verify normalized weights sum to 100%
        applied = score_data['weights_applied']
        total_pct = applied['rating_pct'] + applied['distance_pct'] + applied['price_pct'] + applied['wait_pct']
        self.assertAlmostEqual(total_pct, 100.0, places=1)

    def test_algorithm_5_haversine_distance(self):
        """
        Verify Haversine straight-line distance:
        - Palghar center (19.6936, 72.7655) to Virar center (19.4700, 72.8000)
        - Distance to self is 0.0 km
        - Symmetry: dist(A, B) == dist(B, A)
        """
        palghar = (19.6936, 72.7655)
        virar = (19.4700, 72.8000)

        dist = calculate_haversine_distance(palghar[0], palghar[1], virar[0], virar[1])
        # Expected distance along Palghar-Virar strip is approx 25.1 km
        self.assertTrue(24.0 <= dist <= 26.5)

        # Distance to self
        self_dist = calculate_haversine_distance(palghar[0], palghar[1], palghar[0], palghar[1])
        self.assertEqual(self_dist, 0.0)

        # Symmetry
        rev_dist = calculate_haversine_distance(virar[0], virar[1], palghar[0], palghar[1])
        self.assertEqual(dist, rev_dist)


from django.urls import reverse
from rest_framework.test import APITestCase, APIClient

class IntegrationAndE2ETests(TestCase):
    def setUp(self):
        # Create Owner & Customer
        self.owner = User.objects.create_user(
            username='e2e_owner',
            password='OwnerPassword@123',
            role='OWNER'
        )
        self.customer = User.objects.create_user(
            username='e2e_customer',
            password='CustomerPassword@123',
            role='CUSTOMER'
        )

        # Create LIVE Pilot Restaurant in Satpati
        self.restaurant = Restaurant.objects.create(
            owner=self.owner,
            name='E2E Satpati Seafood Port',
            slug='e2e-satpati-seafood-port',
            description='Harbor fresh fish',
            cuisine_type='Koli Seafood',
            address='Harbor Jetty',
            locality='Satpati',
            latitude=19.7345,
            longitude=72.7050,
            price_range='₹₹',
            phone='9823011111',
            average_rating=4.7,
            waqt_status='LIVE',
            claim_status='VERIFIED',
            is_demo=True,
            is_verified=True,
        )

        # Create Unconnected LISTED directory restaurant
        self.listed_restaurant = Restaurant.objects.create(
            name='Kelva Beach Snack Shack',
            slug='kelva-beach-snack-shack',
            description='Authentic beach shack',
            cuisine_type='Coastal Fast Food',
            address='Kelva Beach Road',
            locality='Kelva',
            latitude=19.6210,
            longitude=72.7310,
            price_range='₹',
            phone='9823099999',
            average_rating=4.3,
            waqt_status='LISTED',
            claim_status='UNCLAIMED',
            owner=None,
            is_verified=True,
        )

        # Tables: Table 1 (cap 2), Table 2 (cap 4)
        self.t1 = RestaurantTable.objects.create(
            restaurant=self.restaurant,
            table_number='1',
            capacity=2,
            status='AVAILABLE'
        )
        self.t2 = RestaurantTable.objects.create(
            restaurant=self.restaurant,
            table_number='2',
            capacity=4,
            status='AVAILABLE'
        )

        # Menu Item
        self.dish = MenuItem.objects.create(
            restaurant=self.restaurant,
            name='Surmai Tawa Fry',
            description='Fresh king fish fry',
            price=380.00,
            category='Fish',
            is_available=True
        )

    def test_landing_page_e2e(self):
        """Landing page renders with editorial branding, pilot tag, and restaurant cards."""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Waqt')
        self.assertContains(response, 'वेळ')
        self.assertContains(response, 'COASTAL CORRIDOR')
        self.assertContains(response, 'E2E Satpati Seafood Port')

    def test_search_and_filter_view(self):
        """Search page filters correctly."""
        response = self.client.get(reverse('restaurants:search'), {'q': 'Satpati'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'E2E Satpati Seafood Port')

        # Negative query
        neg_response = self.client.get(reverse('restaurants:search'), {'q': 'NonExistentDishXYZ'})
        self.assertContains(neg_response, 'No coastal eateries found for this filter')

    def test_weighted_comparison_view(self):
        """Weighted comparison page renders with dynamic sliders."""
        response = self.client.get(reverse('restaurants:compare'), {
            'w_rating': 40,
            'w_distance': 30,
            'w_price': 15,
            'w_wait': 15
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Weighted Comparison Algorithm')
        self.assertContains(response, 'E2E Satpati Seafood Port')

    def test_restaurant_detail_view(self):
        """Detail page shows live table grid and menu."""
        response = self.client.get(reverse('restaurants:detail', kwargs={'slug': self.restaurant.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Surmai Tawa Fry')
        self.assertContains(response, 'Table 1')
        self.assertContains(response, 'Table 2')

    def test_reservation_booking_greedy_flow(self):
        """Customer logs in, books a table for party of 3, Greedy Allocation assigns Table 2 (cap 4)."""
        self.client.login(username='e2e_customer', password='CustomerPassword@123')
        
        url = reverse('reservations:book', kwargs={'slug': self.restaurant.slug})
        post_data = {
            'party_size': 3,
            'reservation_date': date.today(),
            'reservation_time': time(19, 30),
            'special_requests': 'Sea view please'
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify reservation created
        res = Reservation.objects.filter(customer=self.customer, restaurant=self.restaurant).first()
        self.assertIsNotNone(res)
        self.assertEqual(res.status, 'CONFIRMED')
        self.assertEqual(res.table, self.t2)
        
        # Table 2 must now be RESERVED
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, 'RESERVED')

    def test_queue_joining_and_polling_api(self):
        """Customer joins live queue and polls API."""
        self.client.login(username='e2e_customer', password='CustomerPassword@123')

        join_url = reverse('queue_system:join', kwargs={'slug': self.restaurant.slug})
        response = self.client.post(join_url, {'party_size': 2}, follow=True)
        self.assertEqual(response.status_code, 200)

        ticket = QueueEntry.objects.filter(customer=self.customer, restaurant=self.restaurant).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.position, 1)

        # Poll status API
        api_url = reverse('queue_system:api_status', kwargs={'pk': ticket.pk})
        api_resp = self.client.get(api_url)
        self.assertEqual(api_resp.status_code, 200)
        data = api_resp.json()
        self.assertEqual(data['ticket_id'], ticket.id)
        self.assertEqual(data['status'], 'WAITING')
        self.assertEqual(data['position'], 1)
        self.assertIn('estimated_wait_minutes', data)

    def test_owner_console_permission_and_analytics(self):
        """Owner can access console and view MAE report; customer is blocked."""
        # As Customer: blocked
        self.client.login(username='e2e_customer', password='CustomerPassword@123')
        cust_resp = self.client.get(reverse('owner_dashboard'), follow=True)
        self.assertContains(cust_resp, 'Access restricted to restaurant owners')

        # As Owner: allowed
        self.client.login(username='e2e_owner', password='OwnerPassword@123')
        owner_resp = self.client.get(reverse('owner_dashboard'))
        self.assertEqual(owner_resp.status_code, 200)
        self.assertContains(owner_resp, 'Host Stand Console')

        # Owner Analytics
        analytics_resp = self.client.get(reverse('owner_analytics'))
        self.assertEqual(analytics_resp.status_code, 200)
        self.assertContains(analytics_resp, 'Algorithm Wait-Time Accuracy (MAE)')

    def test_unconnected_restaurant_blocks_booking_honestly(self):
        """Honesty Rule: Unconnected LISTED restaurant strictly blocks reservation attempts."""
        self.client.login(username='e2e_customer', password='CustomerPassword@123')
        url = reverse('reservations:book', kwargs={'slug': self.listed_restaurant.slug})
        response = self.client.post(url, {
            'party_size': 2,
            'reservation_date': date.today(),
            'reservation_time': time(19, 0)
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is not currently connected to the Waqt live network')
        self.assertEqual(Reservation.objects.filter(restaurant=self.listed_restaurant).count(), 0)

    def test_unconnected_restaurant_blocks_queuing_honestly(self):
        """Honesty Rule: Unconnected LISTED restaurant strictly blocks queue joins."""
        self.client.login(username='e2e_customer', password='CustomerPassword@123')
        url = reverse('queue_system:join', kwargs={'slug': self.listed_restaurant.slug})
        response = self.client.post(url, {'party_size': 2}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is not connected to the Waqt live queue network')
        self.assertEqual(QueueEntry.objects.filter(restaurant=self.listed_restaurant).count(), 0)

    def test_unconnected_restaurant_live_table_api_honesty(self):
        """Live table API honesty: returns is_live=False for directory listings without fake tables."""
        api_url = reverse('restaurants:api_live_tables', kwargs={'restaurant_id': self.listed_restaurant.id})
        response = self.client.get(api_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['is_live'])
        self.assertEqual(data['waqt_status'], 'LISTED')
        self.assertEqual(len(data['tables']), 0)

    def test_restaurant_claim_and_admin_approval_workflow(self):
        """Owner claim flow: Customer claims unowned listing, admin approves, upgrades to LIVE & OWNER."""
        claimant = User.objects.create_user(username='prospective_owner', password='Password@123', role='CUSTOMER')
        self.client.login(username='prospective_owner', password='Password@123')

        claim_url = reverse('restaurants:claim', kwargs={'slug': self.listed_restaurant.slug})
        post_data = {
            'full_name': 'Koli Restaurateur',
            'phone': '+91 98230 44556',
            'role_in_business': 'Proprietor',
            'verification_notes': 'FSSAI Lic: 11520020000123, GSTIN: 27AAAAA0000A1Z5'
        }
        resp = self.client.post(claim_url, post_data, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Claim was created with PENDING
        claim = RestaurantClaim.objects.filter(restaurant=self.listed_restaurant, claimant=claimant).first()
        self.assertIsNotNone(claim)
        self.assertEqual(claim.status, 'PENDING')
        self.listed_restaurant.refresh_from_db()
        self.assertEqual(self.listed_restaurant.claim_status, 'PENDING')

        # Admin approval action
        from restaurants.admin import approve_claims
        from unittest.mock import MagicMock
        mock_modeladmin = MagicMock()
        mock_request = MagicMock()
        approve_claims(mock_modeladmin, mock_request, RestaurantClaim.objects.filter(id=claim.id))

        # Check upgraded restaurant and user
        self.listed_restaurant.refresh_from_db()
        claim.refresh_from_db()
        claimant.refresh_from_db()
        self.assertEqual(claim.status, 'VERIFIED')
        self.assertEqual(self.listed_restaurant.waqt_status, 'LIVE')
        self.assertEqual(self.listed_restaurant.claim_status, 'VERIFIED')
        self.assertEqual(self.listed_restaurant.owner, claimant)
        self.assertEqual(claimant.role, 'OWNER')
