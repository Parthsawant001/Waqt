"""
Comprehensive Seed Data Command for Waqt (Palghar-Virar Coastal Pilot)
=====================================================================
Seeds authentic Koli coastal restaurants, tables, menus, users, historical turnovers,
active reservations, and live queue tickets.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date, time
from restaurants.models import Restaurant, RestaurantTable, MenuItem, Review
from reservations.models import Reservation
from queue_system.models import QueueEntry, TableTurnover

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds initial authentic Palghar-Virar coastal restaurants, tables, menus, and turnover logs"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Waqt Palghar-Virar coastal platform data..."))

        # 1. Superuser
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@waqt.local',
                'first_name': 'Waqt',
                'last_name': 'Administrator',
                'role': 'OWNER',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('Admin@123')
        admin_user.save()

        # 2. Customers
        customers_data = [
            ('koli_foodie', 'koli.foodie@gmail.com', 'Suraj', 'Patil', '9823011122'),
            ('virar_traveller', 'virar.food@gmail.com', 'Neha', 'Koli', '9823022233'),
            ('mumbai_gourmet', 'amit.meher@gmail.com', 'Amit', 'Meher', '9823033344'),
        ]
        created_customers = []
        for username, email, fn, ln, ph in customers_data:
            c, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': fn,
                    'last_name': ln,
                    'role': 'CUSTOMER',
                    'phone': ph
                }
            )
            c.set_password('Foodie@123')
            c.save()
            created_customers.append(c)

        # 3. Owners
        owners_data = [
            ('satpati_owner', 'bhavesh.koli@satpatiseafood.in', 'Bhavesh', 'Koli', '9823044455'),
            ('kelva_owner', 'kishor.tandel@kelvakinara.in', 'Kishor', 'Tandel', '9823055566'),
            ('arnala_owner', 'vasant.vaity@arnalasagar.in', 'Vasant', 'Vaity', '9823066677'),
            ('shirgaon_owner', 'rajan.nakhwa@shirgaonfish.in', 'Rajan', 'Nakhwa', '9823077788'),
            ('vasai_owner', 'pravin.tare@vasaicreek.in', 'Pravin', 'Tare', '9823088899'),
            ('dahanu_owner', 'ganesh.save@dahanuseafood.in', 'Ganesh', 'Save', '9823099900'),
        ]
        created_owners = {}
        for username, email, fn, ln, ph in owners_data:
            o, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': fn,
                    'last_name': ln,
                    'role': 'OWNER',
                    'phone': ph
                }
            )
            o.set_password('Owner@123')
            o.save()
            created_owners[username] = o

        # 4. Coastal Restaurants
        restaurants_spec = [
            {
                'owner': created_owners['satpati_owner'],
                'name': 'Satpati Koli Seafood Bhavan',
                'description': 'Direct harbor catch of the Arabian Sea. Famous for whole Pomfret tawa fry, fresh Surmai coastal curry, and crunchy Bombil fried in coarse rice flour.',
                'cuisine_type': 'Traditional Koli Coastal Seafood',
                'address': 'Main Jetty Road, Near Fishing Port, Satpati',
                'locality': 'Satpati',
                'latitude': 19.734500,
                'longitude': 72.705000,
                'price_range': '₹₹',
                'phone': '+91 98230 44455',
                'opening_time': time(11, 30),
                'closing_time': time(23, 0),
                'average_rating': 4.8,
                'hero_image': '/static/images/satpati-hero.jpg',
            },
            {
                'owner': created_owners['kelva_owner'],
                'name': 'Kelva Kinara Garden Restaurant',
                'description': 'Nestled under swaying coconut palms near Kelva beach. Renowned for rich coconut crab curries, Jawla bhakri, and chilled home-churned Solkadhi.',
                'cuisine_type': 'Agri-Koli & Malvani Delicacies',
                'address': 'Kelva Beach Seaface, Opp. Pine Plantation, Kelva',
                'locality': 'Kelva',
                'latitude': 19.617500,
                'longitude': 72.731500,
                'price_range': '₹₹',
                'phone': '+91 98230 55566',
                'opening_time': time(11, 0),
                'closing_time': time(22, 30),
                'average_rating': 4.6,
                'hero_image': '/static/images/kelva-hero.jpg',
            },
            {
                'owner': created_owners['arnala_owner'],
                'name': 'Arnala Sagar Kinara',
                'description': 'Waterfront dining overlooking Arnala Fort. Features fresh tiger prawns koliwada, stuffed squid (kalwa), and signature sea-salt seasoned fish thalis.',
                'cuisine_type': 'Koli Fresh Seafood & Thali',
                'address': 'Arnala Fort Coastal Road, Near Ferry Wharf, Virar West',
                'locality': 'Arnala, Virar',
                'latitude': 19.463200,
                'longitude': 72.784500,
                'price_range': '₹₹',
                'phone': '+91 98230 66677',
                'opening_time': time(11, 0),
                'closing_time': time(23, 30),
                'average_rating': 4.7,
                'hero_image': '/static/images/arnala-hero.jpg',
            },
            {
                'owner': created_owners['shirgaon_owner'],
                'name': 'Shirgaon Fort Fish House',
                'description': 'Authentic Koli household recipes passed through generations. Wood-fired Tisrya (clams) masala, smoked dry-fish chutney, and hot Tandlachi Bhakri.',
                'cuisine_type': 'Rustic Koli Heritage',
                'address': 'Old Fort Bund Road, Shirgaon Village, Palghar',
                'locality': 'Shirgaon',
                'latitude': 19.702000,
                'longitude': 72.721000,
                'price_range': '₹',
                'phone': '+91 98230 77788',
                'opening_time': time(12, 0),
                'closing_time': time(22, 0),
                'average_rating': 4.5,
                'hero_image': '/static/images/shirgaon-hero.jpg',
            },
            {
                'owner': created_owners['vasai_owner'],
                'name': 'Vasai Creek Seafood Kitchen',
                'description': 'Premium coastal dining highlighting the heritage of Vasai Portuguese-Koli fusion. Ghol fish curry, butter garlic prawns, and coconut-milk crab.',
                'cuisine_type': 'Vasai Coastal & Malvani',
                'address': 'Bhuigaon Beach Road, Vasai West',
                'locality': 'Vasai',
                'latitude': 19.362000,
                'longitude': 72.812000,
                'price_range': '₹₹₹',
                'phone': '+91 98230 88899',
                'opening_time': time(11, 30),
                'closing_time': time(23, 30),
                'average_rating': 4.9,
                'hero_image': '/static/images/vasai-hero.jpg',
            },
            {
                'owner': created_owners['dahanu_owner'],
                'name': 'Dahanu Beach Seafood Retreat',
                'description': 'Scenic retreat right on the long sandy Dahanu shore. Specializing in king prawns, coastal vegetarian chiku halwa, and Malvani fish feasts.',
                'cuisine_type': 'North Konkan & Koli Seafood',
                'address': 'Sea Face Road, Near Bordi Crossing, Dahanu',
                'locality': 'Dahanu',
                'latitude': 19.972000,
                'longitude': 72.730000,
                'price_range': '₹₹',
                'phone': '+91 98230 99900',
                'opening_time': time(11, 0),
                'closing_time': time(22, 30),
                'average_rating': 4.4,
                'hero_image': '/static/images/dahanu-hero.jpg',
            },
        ]

        saved_restaurants = []
        for r_spec in restaurants_spec:
            r_spec['is_demo'] = True
            r_spec['waqt_status'] = 'LIVE'
            r_spec['claim_status'] = 'VERIFIED'
            r_spec['is_verified'] = True
            rest, created = Restaurant.objects.get_or_create(
                name=r_spec['name'],
                defaults=r_spec
            )
            if not created:
                for k, v in r_spec.items():
                    setattr(rest, k, v)
                rest.save()
            saved_restaurants.append(rest)
            self.stdout.write(f"  Restaurant: {rest.name} [LIVE DEMO]")

        # 5. Tables for each restaurant
        # Table configurations: 2x 2-seaters, 3x 4-seaters, 2x 6-seaters, 1x 8-seater
        table_configs = [
            ('1', 2, 'AVAILABLE'),
            ('2', 2, 'OCCUPIED'),
            ('3', 4, 'AVAILABLE'),
            ('4', 4, 'AVAILABLE'),
            ('5', 4, 'RESERVED'),
            ('6', 6, 'AVAILABLE'),
            ('7', 6, 'OCCUPIED'),
            ('8', 8, 'AVAILABLE'),
        ]

        for rest in saved_restaurants:
            for t_num, cap, stat in table_configs:
                RestaurantTable.objects.get_or_create(
                    restaurant=rest,
                    table_number=t_num,
                    defaults={'capacity': cap, 'status': stat}
                )

        # 6. Menus with coastal categories
        sample_dishes = [
            ('Surmai Tawa Fry (King Fish)', 'Thick cut fresh Arabian King Fish marinated in authentic Koli bottle masala, shallow pan fried in coconut oil.', 380.00, 'Fish'),
            ('Paplet (Pomfret) Fry', 'Whole Silver Pomfret coated in spicy coarse semolina and rice crust, crisp outside and succulent inside.', 450.00, 'Fish'),
            ('Crispy Bombil Fry (Bombay Duck)', 'Fresh local Bombay duck marinated with lemon, ginger-garlic, fried till golden crispy perfection.', 260.00, 'Fish'),
            ('Kolambi Koliwada (Prawns)', 'Crunchy deep-fried tiger prawns dipped in tangy spiced batter with ajwain and lemon.', 340.00, 'Prawns'),
            ('Kolambi Rassa (Prawns Curry)', 'Juicy sea prawns simmered in fiery toasted coconut, garlic, and triphala gravy.', 320.00, 'Prawns'),
            ('Chimbori (Crab) Masala', 'Fresh coastal Mud Crab simmered in thick roasted coconut, black pepper, and coriander spice paste.', 480.00, 'Crab'),
            ('Tisrya (Clams) Sukka', 'Fresh clams extracted daily from local creek bed, tossed in dry coconut shreds and Koli masala.', 290.00, 'Seafood'),
            ('Koli Special Surmai Thali', 'Includes Surmai Fry, Prawns Curry, Solkadhi, 2 hot Tandlachi Bhakris, Indrayani Steamed Rice, and salad.', 420.00, 'Thali'),
            ('Grand Coastal Seafood Mahathali', 'Lavish coastal feast: Pomfret Fry, Crab Masala, Prawns Sukka, Bombil Fry, Solkadhi, Rice, and Bhakri.', 650.00, 'Thali'),
            ('Jawla Bhakri Combo', 'Traditional sun-dried tiny shrimps tossed with raw onions and green chillies, served with piping hot rice bread.', 190.00, 'Koli Special'),
            ('Fresh Solkadhi (Glass)', 'Digestive nectar crafted with fresh pressed coconut milk, sour purple kokum, garlic, and fresh green coriander.', 70.00, 'Drinks'),
            ('Kokum Cooler (Glass)', 'Sweet and tart chilled summer beverage infused with cumin and coastal rock salt.', 60.00, 'Drinks'),
            ('Ukdiche Modak (2 Pcs)', 'Steamed delicate rice flour dumplings stuffed with freshly grated coconut and organic jaggery, drizzled with pure ghee.', 120.00, 'Desserts'),
        ]

        for rest in saved_restaurants:
            for d_name, desc, price, cat in sample_dishes:
                MenuItem.objects.get_or_create(
                    restaurant=rest,
                    name=d_name,
                    defaults={
                        'description': desc,
                        'price': price,
                        'category': cat,
                        'is_available': True
                    }
                )

        # 7. Historical TableTurnover logs (to power Algorithm 3 & MAE Analytics)
        now = timezone.now()
        for rest in saved_restaurants:
            tables = list(rest.tables.all())
            if not tables:
                continue

            # Historical completed turnovers over last 7 days
            turnover_samples = [
                (2, 28.5),
                (2, 32.0),
                (2, 26.0),
                (4, 42.0),
                (4, 46.5),
                (4, 39.0),
                (6, 58.0),
                (6, 64.0),
                (8, 76.0),
            ]

            for idx, (p_size, dur) in enumerate(turnover_samples):
                t = tables[idx % len(tables)]
                occupied_time = now - timedelta(days=(idx % 5) + 1, hours=(idx % 8) + 2)
                freed_time = occupied_time + timedelta(minutes=dur)
                TableTurnover.objects.get_or_create(
                    restaurant=rest,
                    table=t,
                    party_size=p_size,
                    occupied_at=occupied_time,
                    defaults={
                        'freed_at': freed_time,
                        'duration_minutes': dur
                    }
                )

        # 8. Seed some initial queue entries and reservations for demonstration
        primary_rest = saved_restaurants[0]
        # Active queue
        QueueEntry.objects.get_or_create(
            customer=created_customers[0],
            restaurant=primary_rest,
            party_size=2,
            defaults={
                'position': 1,
                'estimated_wait_minutes': 12,
                'status': 'WAITING',
                'joined_at': now - timedelta(minutes=10)
            }
        )
        QueueEntry.objects.get_or_create(
            customer=created_customers[1],
            restaurant=primary_rest,
            party_size=4,
            defaults={
                'position': 2,
                'estimated_wait_minutes': 24,
                'status': 'WAITING',
                'joined_at': now - timedelta(minutes=5)
            }
        )

        # Seated/Completed queue entries with actual vs predicted wait (for MAE metric)
        for c, p_size, est_w, act_w in [
            (created_customers[2], 2, 15, 14.2),
            (created_customers[0], 4, 30, 32.5),
            (created_customers[1], 2, 20, 18.0),
        ]:
            j_time = now - timedelta(hours=3)
            s_time = j_time + timedelta(minutes=act_w)
            QueueEntry.objects.create(
                customer=c,
                restaurant=primary_rest,
                party_size=p_size,
                position=0,
                estimated_wait_minutes=est_w,
                status='SEATED',
                joined_at=j_time,
                called_at=j_time + timedelta(minutes=act_w - 2),
                seated_at=s_time
            )

        # Sample upcoming reservation
        res_table = primary_rest.tables.filter(capacity=4).first()
        Reservation.objects.get_or_create(
            customer=created_customers[0],
            restaurant=primary_rest,
            reservation_date=date.today() + timedelta(days=1),
            reservation_time=time(19, 30),
            defaults={
                'party_size': 4,
                'table': res_table,
                'status': 'CONFIRMED',
                'special_requests': 'Please keep sea-facing table if possible; ordering Pomfret Thalis.'
            }
        )

        # Sample reviews
        Review.objects.get_or_create(
            customer=created_customers[0],
            restaurant=primary_rest,
            defaults={
                'rating': 5,
                'comment': 'Best Surmai Fry in Satpati! The table was ready right as we arrived from Virar.'
            }
        )
        Review.objects.get_or_create(
            customer=created_customers[1],
            restaurant=saved_restaurants[1],
            defaults={
                'rating': 5,
                'comment': 'Outstanding coconut crab curry and fresh Solkadhi. Love knowing the table status beforehand.'
            }
        )


        # 9. Kitchen Orders (DEMO DATA)
        from restaurants.models import KitchenOrder, KitchenOrderItem
        import random
        for rest in saved_restaurants:
            menu_items = list(rest.menu_items.all())
            occupied_tables = list(rest.tables.filter(status='OCCUPIED'))
            for idx, table in enumerate(occupied_tables):
                status = 'PREPARING' if idx % 2 == 0 else 'NEW'
                ko = KitchenOrder.objects.create(
                    restaurant=rest,
                    table=table,
                    order_number=f"DEMO-{random.randint(1000, 9999)}",
                    status=status,
                    notes='DEMO DATA'
                )
                if menu_items:
                    m1 = random.choice(menu_items)
                    m2 = random.choice(menu_items)
                    KitchenOrderItem.objects.create(kitchen_order=ko, menu_item=m1, quantity=2, unit_price=m1.price)
                    KitchenOrderItem.objects.create(kitchen_order=ko, menu_item=m2, quantity=1, unit_price=m2.price)

        self.stdout.write(self.style.SUCCESS("Successfully seeded Waqt coastal platform!"))
