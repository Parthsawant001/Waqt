import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q
from .models import Restaurant, RestaurantTable, MenuItem, Review, RestaurantClaim
from .forms import RestaurantTableForm, MenuItemForm, ReviewForm, RestaurantClaimForm
from core.services.geo_service import calculate_haversine_distance, get_default_coastal_coords
from core.services.wait_time_service import estimate_queue_wait_minutes
from core.services.comparison_service import calculate_waqt_score, rank_restaurants_weighted
from reservations.models import Reservation
from queue_system.models import QueueEntry

def landing_index_view(request):
    """
    Public Landing Page:
    - Editorial Luxury Coastal Hero
    - Palghar-Virar-Dahanu coastal corridor stats
    - Connected restaurants with live table capacity snapshot
    - Verified Coastal Directory
    - Interactive Leaflet coordinates with live/directory dual pins
    - Algorithm explanation
    """
    all_active = Restaurant.objects.filter(is_active=True).prefetch_related('tables', 'queue_entries')
    default_lat, default_lon = get_default_coastal_coords()

    total_restaurants = all_active.count()
    live_restaurants = []
    directory_restaurants = []
    map_pins = []

    corridor_regions = ['All', 'Virar', 'Vasai', 'Nalasopara', 'Palghar', 'Kelva', 'Boisar', 'Tarapur', 'Dahanu']

    for r in all_active:
        dist = calculate_haversine_distance(default_lat, default_lon, float(r.latitude), float(r.longitude))
        is_conn = r.is_connected_to_waqt()
        wait = estimate_queue_wait_minutes(r, party_size=2) if is_conn else None

        item_data = {
            'obj': r,
            'is_connected': is_conn,
            'waqt_status': r.waqt_status,
            'distance_km': dist,
            'wait_minutes': wait,
            'available_tables': r.available_tables() if is_conn else None,
            'total_tables': r.total_tables() if is_conn else None,
            'waiting_queue': r.waiting_queue_count() if is_conn else None,
            'rating': float(r.external_rating or r.average_rating or 4.2),
        }

        if is_conn:
            live_restaurants.append(item_data)
        else:
            directory_restaurants.append(item_data)

        map_pins.append({
            'name': r.name,
            'slug': r.slug,
            'locality': r.locality,
            'cuisine': r.cuisine_type,
            'lat': float(r.latitude),
            'lon': float(r.longitude),
            'rating': float(r.external_rating or r.average_rating or 4.2),
            'is_connected': is_conn,
            'waqt_status': r.waqt_status,
            'available_tables': r.available_tables() if is_conn else None,
            'wait_minutes': wait,
            'phone': r.phone,
            'address': r.address,
        })

    context = {
        'total_count': total_restaurants,
        'live_count': len(live_restaurants),
        'directory_count': len(directory_restaurants),
        'live_restaurants': live_restaurants,
        'directory_restaurants': directory_restaurants,
        'all_restaurants': live_restaurants + directory_restaurants,
        'corridor_regions': corridor_regions,
        'map_pins_json': json.dumps(map_pins),
        'default_lat': default_lat,
        'default_lon': default_lon,
    }
    return render(request, 'landing/index.html', context)


def restaurant_search_view(request):
    """
    Find a Table & Directory Search:
    Filters by cuisine, price, locality/region, connection status, and rating.
    Sorts by Recommended (Waqt Score), Distance, Rating, Lowest Wait, Price.
    """
    restaurants = Restaurant.objects.filter(is_active=True)
    
    query = request.GET.get('q', '').strip()
    cuisine = request.GET.get('cuisine', '').strip()
    price = request.GET.get('price', '').strip()
    locality = request.GET.get('locality', '').strip()
    status_filter = request.GET.get('status', '').strip()
    min_rating = request.GET.get('min_rating', '').strip()
    sort_by = request.GET.get('sort', 'recommended')

    try:
        user_lat = float(request.GET.get('lat', get_default_coastal_coords()[0]))
        user_lon = float(request.GET.get('lon', get_default_coastal_coords()[1]))
    except (ValueError, TypeError):
        user_lat, user_lon = get_default_coastal_coords()

    if query:
        restaurants = restaurants.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(locality__icontains=query) |
            Q(city__icontains=query) |
            Q(cuisine_type__icontains=query)
        )
    if cuisine:
        restaurants = restaurants.filter(cuisine_type__icontains=cuisine)
    if price:
        restaurants = restaurants.filter(price_range=price)
    if locality and locality.lower() != 'all':
        restaurants = restaurants.filter(
            Q(locality__icontains=locality) | Q(city__icontains=locality)
        )
    if status_filter == 'live':
        restaurants = restaurants.filter(waqt_status__in=['LIVE', 'DEMO'])
    elif status_filter == 'listed':
        restaurants = restaurants.filter(waqt_status='LISTED')

    if min_rating:
        try:
            r_val = float(min_rating)
            restaurants = restaurants.filter(
                Q(average_rating__gte=r_val) | Q(external_rating__gte=r_val)
            )
        except ValueError:
            pass

    annotated = []
    for r in restaurants:
        dist = calculate_haversine_distance(user_lat, user_lon, float(r.latitude), float(r.longitude))
        is_conn = r.is_connected_to_waqt()
        wait = estimate_queue_wait_minutes(r, party_size=2) if is_conn else None
        score_data = calculate_waqt_score(r, user_lat, user_lon)
        effective_rating = float(r.external_rating or r.average_rating or 4.0)

        annotated.append({
            'obj': r,
            'is_connected': is_conn,
            'distance_km': dist,
            'wait_minutes': wait,
            'waqt_score': score_data['waqt_score'] if is_conn else round(effective_rating * 15, 1),
            'score_breakdown': score_data['breakdown'] if is_conn else {},
            'available_tables': r.available_tables() if is_conn else None,
            'total_tables': r.total_tables() if is_conn else None,
            'waiting_queue': r.waiting_queue_count() if is_conn else None,
            'effective_rating': effective_rating,
        })

    # Sorting
    if sort_by == 'distance':
        annotated.sort(key=lambda x: x['distance_km'])
    elif sort_by == 'rating':
        annotated.sort(key=lambda x: x['effective_rating'], reverse=True)
    elif sort_by == 'wait':
        annotated.sort(key=lambda x: (x['wait_minutes'] is None, x['wait_minutes'] or 999))
    elif sort_by == 'price':
        tier_order = {'₹': 1, '₹₹': 2, '₹₹₹': 3, '₹₹₹₹': 4}
        annotated.sort(key=lambda x: tier_order.get(x['obj'].price_range, 2))
    else:  # 'recommended'
        annotated.sort(key=lambda x: (x['is_connected'], x['waqt_score']), reverse=True)

    localities = ['All', 'Virar', 'Vasai', 'Nalasopara', 'Palghar', 'Kelva', 'Boisar', 'Tarapur', 'Dahanu']

    map_pins = []
    for item in annotated:
        r = item['obj']
        map_pins.append({
            'name': r.name,
            'slug': r.slug,
            'locality': r.locality,
            'cuisine': r.cuisine_type,
            'lat': float(r.latitude),
            'lon': float(r.longitude),
            'rating': item['effective_rating'],
            'is_connected': item['is_connected'],
            'available_tables': item['available_tables'],
            'total_tables': item['total_tables'],
            'wait_minutes': item['wait_minutes'],
            'price_range': r.price_range,
        })

    context = {
        'restaurants': annotated,
        'query': query,
        'cuisine': cuisine,
        'price': price,
        'locality': locality,
        'status_filter': status_filter,
        'min_rating': min_rating,
        'sort_by': sort_by,
        'user_lat': user_lat,
        'user_lon': user_lon,
        'localities': localities,
        'total_count': len(annotated),
        'map_pins_json': json.dumps(map_pins),
    }
    return render(request, 'customer/search.html', context)


COASTAL_HUBS = [
    {'name': 'Virar (Arnala / West)', 'lat': 19.4632, 'lon': 72.7845},
    {'name': 'Palghar Railway Station', 'lat': 19.6967, 'lon': 72.7699},
    {'name': 'Satpati Fishing Harbor', 'lat': 19.7345, 'lon': 72.7050},
    {'name': 'Kelva Beach & Fort', 'lat': 19.6210, 'lon': 72.7310},
    {'name': 'Vasai Creek & West', 'lat': 19.3620, 'lon': 72.8020},
    {'name': 'Boisar / Tarapur MIDC', 'lat': 19.8020, 'lon': 72.7540},
    {'name': 'Dahanu Coastal Shores', 'lat': 19.9720, 'lon': 72.7320},
]


def restaurant_compare_view(request):
    """
    Weighted Restaurant Comparison Tool:
    Allows diners to configure sliders for Rating, Distance, Price, and Waiting Time.
    Displays dynamic transparent Waqt score breakdown, side-by-side comparison,
    and interactive Google Maps visualization.
    """
    try:
        user_lat = float(request.GET.get('lat', get_default_coastal_coords()[0]))
        user_lon = float(request.GET.get('lon', get_default_coastal_coords()[1]))
    except (ValueError, TypeError):
        user_lat, user_lon = get_default_coastal_coords()

    w_rating = float(request.GET.get('w_rating', 30))
    w_distance = float(request.GET.get('w_distance', 25))
    w_price = float(request.GET.get('w_price', 20))
    w_wait = float(request.GET.get('w_wait', 25))

    raw_selected = request.GET.get('selected', '') or request.GET.get('compare', '')
    selected_slugs = [s.strip() for s in raw_selected.split(',') if s.strip()]
    selected_ids = [int(i) for i in request.GET.get('ids', '').split(',') if i.strip().isdigit()]

    restaurants = Restaurant.objects.filter(is_active=True)
    ranked = rank_restaurants_weighted(
        restaurants,
        customer_lat=user_lat,
        customer_lon=user_lon,
        w_rating=w_rating,
        w_distance=w_distance,
        w_price=w_price,
        w_wait=w_wait
    )

    tier_map = {'₹': 1, '₹₹': 2, '₹₹₹': 3, '₹₹₹₹': 4}
    compare_items = []
    for r in restaurants:
        is_conn = r.is_connected_to_waqt()
        wait = estimate_queue_wait_minutes(r, party_size=2) if is_conn else 15
        rating = float(r.external_rating or r.average_rating or 4.0)
        is_sel = (r.slug in selected_slugs or r.id in selected_ids)
        compare_items.append({
            'id': r.id,
            'name': r.name,
            'slug': r.slug,
            'locality': r.locality,
            'address': r.address,
            'phone': r.phone,
            'cuisine': r.cuisine_type,
            'price_range': r.price_range,
            'price_tier': tier_map.get(r.price_range, 2),
            'rating': rating,
            'lat': float(r.latitude),
            'lon': float(r.longitude),
            'is_connected': is_conn,
            'available_tables': r.available_tables() if is_conn else 0,
            'total_tables': r.total_tables() if is_conn else 0,
            'waiting_queue': r.waiting_queue_count() if is_conn else 0,
            'wait_minutes': wait,
            'selected': is_sel,
        })

    # If no initial selection given, default preselect top 2 for instant comparison
    if not any(item['selected'] for item in compare_items) and len(ranked) >= 2:
        top_ids = [ranked[0]['restaurant_id'], ranked[1]['restaurant_id']]
        for item in compare_items:
            if item['id'] in top_ids:
                item['selected'] = True

    context = {
        'ranked_restaurants': ranked,
        'user_lat': user_lat,
        'user_lon': user_lon,
        'w_rating': int(w_rating),
        'w_distance': int(w_distance),
        'w_price': int(w_price),
        'w_wait': int(w_wait),
        'coastal_hubs': COASTAL_HUBS,
        'compare_items_json': json.dumps(compare_items),
        'selected_slugs': selected_slugs,
        'total_count': restaurants.count(),
    }
    return render(request, 'customer/compare.html', context)


def restaurant_detail_view(request, slug):
    """
    Restaurant Detail Page:
    - Hero, address, distance, live availability or directory status
    - Real-time Table floor grid (for connected restaurants)
    - Claim CTA (for unverified/unconnected listings)
    - Categorized coastal menu & reviews
    """
    restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
    is_connected = restaurant.is_connected_to_waqt()
    
    default_lat, default_lon = get_default_coastal_coords()
    distance_km = calculate_haversine_distance(
        default_lat, default_lon,
        float(restaurant.latitude), float(restaurant.longitude)
    )
    current_wait = estimate_queue_wait_minutes(restaurant, party_size=2) if is_connected else None
    score_data = calculate_waqt_score(restaurant, default_lat, default_lon) if is_connected else None

    tables = restaurant.tables.all().order_by('table_number') if is_connected else []
    
    menu_items = restaurant.menu_items.filter(is_available=True)
    categorized_menu = {}
    for item in menu_items:
        categorized_menu.setdefault(item.get_category_display(), []).append(item)

    reviews = restaurant.reviews.all()[:8]
    review_form = ReviewForm()

    user_claim = None
    if request.user.is_authenticated:
        user_claim = RestaurantClaim.objects.filter(restaurant=restaurant, claimant=request.user).first()

    context = {
        'restaurant': restaurant,
        'is_connected': is_connected,
        'distance_km': distance_km,
        'current_wait': current_wait,
        'waqt_score': score_data['waqt_score'] if score_data else None,
        'score_breakdown': score_data['breakdown'] if score_data else None,
        'tables': tables,
        'categorized_menu': categorized_menu,
        'reviews': reviews,
        'review_form': review_form,
        'user_claim': user_claim,
    }
    return render(request, 'customer/restaurant_detail.html', context)


@login_required
def claim_restaurant_view(request, slug):
    """
    Restaurant Owner Claim Flow:
    Allows verified restaurateurs along the Virar-Dahanu corridor to claim their public listing,
    submit business verification notes (FSSAI, GSTIN, bills), and activate Waqt live capacity.
    """
    restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)

    if restaurant.claim_status == 'VERIFIED' and restaurant.owner:
        messages.info(request, f"'{restaurant.name}' has already been claimed and verified by its proprietor.")
        return redirect('restaurants:detail', slug=slug)

    existing_claim = RestaurantClaim.objects.filter(
        restaurant=restaurant,
        claimant=request.user,
        status='PENDING'
    ).first()

    if request.method == 'POST':
        form = RestaurantClaimForm(request.POST)
        if form.is_valid():
            if existing_claim:
                messages.warning(request, "You already have a pending claim submission for this restaurant.")
                return redirect('restaurants:detail', slug=slug)

            RestaurantClaim.objects.create(
                restaurant=restaurant,
                claimant=request.user,
                full_name=form.cleaned_data['full_name'],
                phone=form.cleaned_data['phone'],
                role_in_business=form.cleaned_data['role_in_business'],
                verification_notes=form.cleaned_data['verification_notes'],
                status='PENDING',
            )
            restaurant.claim_status = 'PENDING'
            restaurant.save(update_fields=['claim_status'])

            messages.success(
                request,
                f"Thank you, {form.cleaned_data['full_name']}. Your ownership claim for '{restaurant.name}' has been received and is pending administrative verification. Once verified, you will gain full access to live table capacity and queue management."
            )
            return redirect('restaurants:detail', slug=slug)
    else:
        initial = {}
        if request.user.get_full_name():
            initial['full_name'] = request.user.get_full_name()
        if hasattr(request.user, 'phone') and request.user.phone:
            initial['phone'] = request.user.phone
        form = RestaurantClaimForm(initial=initial)

    context = {
        'restaurant': restaurant,
        'form': form,
        'existing_claim': existing_claim,
    }
    return render(request, 'restaurants/claim_restaurant.html', context)


@login_required
def add_review_view(request, slug):
    restaurant = get_object_or_404(Restaurant, slug=slug)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.customer = request.user
            review.restaurant = restaurant
            review.save()
            messages.success(request, "Thank you for sharing your authentic coastal review!")
        else:
            messages.error(request, "Please provide a valid rating (1-5) and feedback.")
    return redirect('restaurants:detail', slug=slug)


# --- OWNER DASHBOARD & FLOOR MANAGEMENT VIEWS ---

@login_required
def owner_dashboard_view(request):
    if not request.user.is_owner():
        messages.error(request, "Access restricted to restaurant owners.")
        return redirect('accounts:dashboard')

    restaurant = Restaurant.objects.filter(owner=request.user).first()
    if not restaurant:
        messages.warning(request, "You haven't claimed a restaurant yet. Search for your restaurant to claim it.")
        return redirect('restaurants:search')

    tables = restaurant.tables.all().order_by('table_number')
    active_queue = restaurant.queue_entries.filter(status__in=['WAITING', 'CALLED']).order_by('position')
    upcoming_reservations = restaurant.reservations.filter(status__in=['PENDING', 'CONFIRMED']).order_by('reservation_date', 'reservation_time')[:5]

    context = {
        'restaurant': restaurant,
        'tables': tables,
        'active_queue': active_queue,
        'upcoming_reservations': upcoming_reservations,
        'available_count': restaurant.available_tables(),
        'occupied_count': restaurant.occupied_tables(),
        'reserved_count': restaurant.reserved_tables(),
        'cleaning_count': restaurant.cleaning_tables(),
        'total_count': restaurant.total_tables(),
    }
    return render(request, 'owner/dashboard.html', context)


@login_required
def owner_table_management_view(request):
    if not request.user.is_owner():
        return HttpResponseForbidden()

    restaurant = Restaurant.objects.filter(owner=request.user).first()
    if not restaurant:
        return redirect('restaurants:search')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            form = RestaurantTableForm(request.POST)
            if form.is_valid():
                table = form.save(commit=False)
                table.restaurant = restaurant
                table.save()
                messages.success(request, f"Table {table.table_number} added successfully.")
                return redirect('owner:tables')
            else:
                messages.error(request, "Invalid table details. Table number must be unique.")
        elif action == 'update_status':
            table_id = request.POST.get('table_id')
            new_status = request.POST.get('status')
            table = get_object_or_404(RestaurantTable, id=table_id, restaurant=restaurant)
            table.status = new_status
            table.save(update_fields=['status'])
            messages.success(request, f"Table {table.table_number} marked as {table.get_status_display()}.")
            return redirect('owner:tables')
        elif action == 'delete':
            table_id = request.POST.get('table_id')
            table = get_object_or_404(RestaurantTable, id=table_id, restaurant=restaurant)
            num = table.table_number
            table.delete()
            messages.success(request, f"Table {num} removed.")
            return redirect('owner:tables')

    form = RestaurantTableForm()
    tables = restaurant.tables.all().order_by('table_number')
    return render(request, 'owner/table_management.html', {
        'restaurant': restaurant,
        'tables': tables,
        'form': form
    })


@login_required
def owner_menu_management_view(request):
    if not request.user.is_owner():
        return HttpResponseForbidden()

    restaurant = Restaurant.objects.filter(owner=request.user).first()
    if not restaurant:
        return redirect('restaurants:search')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            form = MenuItemForm(request.POST)
            if form.is_valid():
                item = form.save(commit=False)
                item.restaurant = restaurant
                item.save()
                messages.success(request, f"Added '{item.name}' to the menu.")
                return redirect('owner:menu')
        elif action == 'toggle_availability':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
            item.is_available = not item.is_available
            item.save(update_fields=['is_available'])
            state = "available" if item.is_available else "sold out"
            messages.info(request, f"'{item.name}' is now marked as {state}.")
            return redirect('owner:menu')
        elif action == 'delete':
            item_id = request.POST.get('item_id')
            item = get_object_or_404(MenuItem, id=item_id, restaurant=restaurant)
            name = item.name
            item.delete()
            messages.success(request, f"'{name}' deleted from menu.")
            return redirect('owner:menu')

    form = MenuItemForm()
    menu_items = restaurant.menu_items.all()
    return render(request, 'owner/menu_management.html', {
        'restaurant': restaurant,
        'menu_items': menu_items,
        'form': form
    })

@login_required
def owner_kitchen_display_view(request):
    if not request.user.is_owner():
        return HttpResponseForbidden()
    
    claim = request.user.restaurant_claims.filter(status='VERIFIED').first()
    if not claim:
        return redirect('restaurants:search')
        
    return render(request, 'owner/kitchen_display.html', {'restaurant': claim.restaurant})
