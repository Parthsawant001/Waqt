from rest_framework import serializers
from .models import Restaurant, RestaurantTable, MenuItem, Review

class RestaurantTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantTable
        fields = ['id', 'table_number', 'capacity', 'status', 'created_at']


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'description', 'price', 'category', 'image', 'is_available']


class RestaurantListSerializer(serializers.ModelSerializer):
    available_tables = serializers.IntegerField(source='available_tables', read_only=True)
    total_tables = serializers.IntegerField(source='total_tables', read_only=True)
    waiting_queue = serializers.IntegerField(source='waiting_queue_count', read_only=True)

    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'slug', 'description', 'cuisine_type', 'address',
            'locality', 'city', 'district', 'latitude', 'longitude', 'price_range', 'phone',
            'opening_time', 'closing_time', 'average_rating', 'hero_image',
            'waqt_status', 'claim_status', 'is_verified', 'is_demo',
            'external_rating', 'external_rating_source', 'source_name', 'source_url', 'website',
            'available_tables', 'total_tables', 'waiting_queue'
        ]
