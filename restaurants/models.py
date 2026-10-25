from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator

class Restaurant(models.Model):
    PRICE_CHOICES = (
        ('₹', 'Budget (Under ₹300 per person)'),
        ('₹₹', 'Moderate (₹300 - ₹700 per person)'),
        ('₹₹₹', 'Premium (₹700 - ₹1500 per person)'),
        ('₹₹₹₹', 'Luxury Coastal Feast (₹1500+ per person)'),
    )

    WAQT_STATUS_CHOICES = (
        ('LIVE', 'Live on Waqt (Floor & Queue Connected)'),
        ('LISTED', 'Listed in Directory (Not Connected)'),
        ('DEMO', 'Waqt Pilot Demo Data'),
    )

    CLAIM_STATUS_CHOICES = (
        ('UNCLAIMED', 'Unclaimed Public Listing'),
        ('PENDING', 'Claim Pending Verification'),
        ('VERIFIED', 'Verified Owner Registered'),
        ('REJECTED', 'Claim Rejected'),
    )

    # Owner can be null for unclaimed public directory listings
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='restaurants')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    cuisine_type = models.CharField(max_length=120, default='Koli Coastal Seafood')
    address = models.CharField(max_length=500)
    locality = models.CharField(max_length=120, help_text="e.g. Virar, Nalasopara, Vasai, Palghar, Boisar, Tarapur, Kelva, Dahanu")
    city = models.CharField(max_length=100, default='Palghar')
    district = models.CharField(max_length=100, default='Palghar')
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, default=19.693600)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, default=72.765500)
    price_range = models.CharField(max_length=10, choices=PRICE_CHOICES, default='₹₹')
    phone = models.CharField(max_length=50, blank=True, default='')
    website = models.URLField(max_length=500, blank=True, null=True)
    
    opening_time = models.TimeField(default='11:00:00')
    closing_time = models.TimeField(default='23:00:00')
    
    # Rating architecture: separates public imported rating from actual Waqt user reviews
    average_rating = models.FloatField(default=4.2, validators=[MinValueValidator(1.0), MaxValueValidator(5.0)])
    external_rating = models.FloatField(null=True, blank=True)
    external_rating_source = models.CharField(max_length=80, blank=True, default='Public Reviews')
    waqt_rating = models.FloatField(null=True, blank=True)

    # Verification & Status Architecture
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=True, help_text="True if business existence is verified from public sources")
    is_demo = models.BooleanField(default=False, help_text="True only for designated test/demo restaurants")
    waqt_status = models.CharField(max_length=20, choices=WAQT_STATUS_CHOICES, default='LISTED')
    claim_status = models.CharField(max_length=25, choices=CLAIM_STATUS_CHOICES, default='UNCLAIMED')
    
    source_url = models.URLField(max_length=600, blank=True, null=True)
    source_name = models.CharField(max_length=100, blank=True, default='Public Coastal Directory')
    last_verified_at = models.DateTimeField(null=True, blank=True)

    hero_image = models.CharField(max_length=500, blank=True, default='/static/images/hero-coastal.jpg')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['locality']),
            models.Index(fields=['waqt_status']),
            models.Index(fields=['cuisine_type']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            if not base_slug:
                base_slug = 'coastal-restaurant'
            slug = base_slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def is_connected_to_waqt(self):
        """Returns True if the restaurant has live floor and queue management enabled."""
        return self.waqt_status in ['LIVE', 'DEMO']

    def total_tables(self):
        return self.tables.count() if self.is_connected_to_waqt() else 0

    def available_tables(self):
        return self.tables.filter(status='AVAILABLE').count() if self.is_connected_to_waqt() else 0

    def occupied_tables(self):
        return self.tables.filter(status='OCCUPIED').count() if self.is_connected_to_waqt() else 0

    def reserved_tables(self):
        return self.tables.filter(status='RESERVED').count() if self.is_connected_to_waqt() else 0

    def cleaning_tables(self):
        return self.tables.filter(status='CLEANING').count() if self.is_connected_to_waqt() else 0

    def waiting_queue_count(self):
        return self.queue_entries.filter(status='WAITING').count() if self.is_connected_to_waqt() else 0

    def __str__(self):
        return f"{self.name} ({self.locality}) [{self.get_waqt_status_display()}]"


class RestaurantClaim(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Verification'),
        ('VERIFIED', 'Verified & Approved'),
        ('REJECTED', 'Rejected'),
    )

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='restaurant_claims')
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    role_in_business = models.CharField(max_length=100, help_text="e.g. Owner, Managing Partner, General Manager")
    verification_notes = models.TextField(help_text="Provide business registration details, FSSAI number, GSTIN, or electric bill reference")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Claim for {self.restaurant.name} by {self.claimant.username} ({self.get_status_display()})"


class RestaurantTable(models.Model):
    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('RESERVED', 'Reserved'),
        ('CLEANING', 'Cleaning'),
        ('OUT_OF_SERVICE', 'Out of Service'),
    )

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_number = models.CharField(max_length=20)
    capacity = models.PositiveIntegerField(default=4)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('restaurant', 'table_number')
        ordering = ['table_number']

    def __str__(self):
        return f"Table {self.table_number} (Cap: {self.capacity}) - {self.get_status_display()}"


class MenuItem(models.Model):
    CATEGORY_CHOICES = (
        ('Seafood', 'Fresh Catch & Seafood'),
        ('Fish', 'Fish Special (Surmai, Pomfret, Rawas)'),
        ('Prawns', 'Prawns (Kolambi)'),
        ('Crab', 'Crab (Kekda)'),
        ('Koli Special', 'Traditional Koli Authentic'),
        ('Malvani', 'Malvani Curries & Sukka'),
        ('Thali', 'Authentic Coastal Thalis'),
        ('Rice', 'Bhakri, Vade & Rice Preparations'),
        ('Vegetarian', 'Coastal Vegetarian & Dal'),
        ('Chicken', 'Chicken (Kombdi)'),
        ('Mutton', 'Mutton Specialties'),
        ('Drinks', 'Solkadhi & Coastal Coolers'),
        ('Desserts', 'Modak & Coastal Sweets'),
        ('Other', 'Other/Extras'),
    )

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Seafood')
    image = models.CharField(max_length=500, blank=True, default='/static/images/dish-fish.jpg')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - ₹{self.price} ({self.restaurant.name})"


class Review(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='reviews')
    reservation = models.OneToOneField('reservations.Reservation', on_delete=models.SET_NULL, null=True, blank=True, related_name='review')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update restaurant waqt_rating & average_rating
        reviews = self.restaurant.reviews.all()
        if reviews.exists():
            avg = sum(r.rating for r in reviews) / reviews.count()
            self.restaurant.waqt_rating = round(avg, 1)
            self.restaurant.average_rating = round(avg, 1)
            self.restaurant.save(update_fields=['average_rating', 'waqt_rating'])

    def __str__(self):
        return f"Review by {self.customer.username} for {self.restaurant.name} ({self.rating}/5)"

class KitchenOrder(models.Model):
    STATUS_CHOICES = (
        ('NEW', 'New'),
        ('ACCEPTED', 'Accepted'),
        ('PREPARING', 'Preparing'),
        ('READY', 'Ready'),
        ('SERVED', 'Served'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='kitchen_orders')
    table = models.ForeignKey(RestaurantTable, on_delete=models.SET_NULL, null=True, blank=True, related_name='kitchen_orders')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='kitchen_orders')
    reservation = models.ForeignKey('reservations.Reservation', on_delete=models.SET_NULL, null=True, blank=True, related_name='kitchen_orders')
    
    order_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    notes = models.TextField(blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    preparing_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Order #{self.order_number} for Table {self.table.table_number if self.table else 'N/A'} - {self.get_status_display()}"


class KitchenOrderItem(models.Model):
    kitchen_order = models.ForeignKey(KitchenOrder, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, help_text="Stored at order time")
    notes = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} (Order #{self.kitchen_order.order_number})"
