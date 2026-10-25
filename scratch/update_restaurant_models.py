import re

with open('restaurants/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update RestaurantTable STATUS_CHOICES
table_status_old = """    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('RESERVED', 'Reserved'),
        ('CLEANING', 'Cleaning'),
    )"""
table_status_new = """    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('RESERVED', 'Reserved'),
        ('CLEANING', 'Cleaning'),
        ('OUT_OF_SERVICE', 'Out of Service'),
    )"""
content = content.replace(table_status_old, table_status_new)

# 2. Update MenuItem CATEGORY_CHOICES
menu_category_old = """    CATEGORY_CHOICES = (
        ('Seafood', 'Fresh Catch & Seafood'),
        ('Fish', 'Fish Special (Surmai, Pomfret, Rawas)'),
        ('Prawns', 'Prawns (Kolambi)'),
        ('Crab', 'Crab (Kekda)'),
        ('Koli Special', 'Traditional Koli Authentic'),
        ('Malvani', 'Malvani Curries & Sukka'),
        ('Rice', 'Bhakri, Vade & Rice Preparations'),
        ('Thali', 'Authentic Coastal Thalis'),
        ('Vegetarian', 'Coastal Vegetarian & Dal'),
        ('Drinks', 'Solkadhi & Coastal Coolers'),
        ('Desserts', 'Modak & Coastal Sweets'),
    )"""
menu_category_new = """    CATEGORY_CHOICES = (
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
    )"""
content = content.replace(menu_category_old, menu_category_new)

# 3. Add KitchenOrder and KitchenOrderItem at the end
kitchen_models = """
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
"""

if "class KitchenOrder(" not in content:
    content += kitchen_models

with open('restaurants/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated restaurants/models.py")
