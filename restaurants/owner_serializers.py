from rest_framework import serializers
from .models import RestaurantTable, MenuItem, KitchenOrder, KitchenOrderItem
from queue_system.models import QueueEntry
from reservations.models import Reservation

class OwnerTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantTable
        fields = ['id', 'table_number', 'capacity', 'status', 'created_at']

class OwnerMenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'description', 'price', 'category', 'is_available', 'image']

class KitchenOrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    class Meta:
        model = KitchenOrderItem
        fields = ['id', 'menu_item', 'menu_item_name', 'quantity', 'unit_price', 'notes', 'subtotal']

class KitchenOrderSerializer(serializers.ModelSerializer):
    items = KitchenOrderItemSerializer(many=True, read_only=True)
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    
    class Meta:
        model = KitchenOrder
        fields = ['id', 'order_number', 'table', 'table_number', 'status', 'notes', 'created_at', 'items']

class OwnerQueueSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    class Meta:
        model = QueueEntry
        fields = ['id', 'customer_name', 'party_size', 'position', 'estimated_wait_minutes', 'status', 'joined_at']

class OwnerReservationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    table_number = serializers.CharField(source='table.table_number', read_only=True)
    class Meta:
        model = Reservation
        fields = ['id', 'customer_name', 'party_size', 'reservation_date', 'reservation_time', 'table_number', 'status']
