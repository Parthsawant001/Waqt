from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Restaurant, RestaurantTable
from .serializers import RestaurantListSerializer, RestaurantTableSerializer
from core.services.comparison_service import calculate_waqt_score
from core.services.geo_service import get_default_coastal_coords

class RestaurantListAPIView(APIView):
    def get(self, request):
        restaurants = Restaurant.objects.filter(is_active=True)
        serializer = RestaurantListSerializer(restaurants, many=True)
        return Response(serializer.data)


class LiveTableStatusAPIView(APIView):
    def get(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        if not restaurant.is_connected_to_waqt():
            return Response({
                'restaurant_id': restaurant.id,
                'restaurant_name': restaurant.name,
                'waqt_status': restaurant.waqt_status,
                'is_live': False,
                'message': 'Restaurant not connected to Waqt - Live capacity unavailable',
                'tables': []
            })

        tables = restaurant.tables.all().order_by('table_number')
        serializer = RestaurantTableSerializer(tables, many=True)
        return Response({
            'restaurant_id': restaurant.id,
            'restaurant_name': restaurant.name,
            'waqt_status': restaurant.waqt_status,
            'is_live': True,
            'total_tables': restaurant.total_tables(),
            'available_tables': restaurant.available_tables(),
            'occupied_tables': restaurant.occupied_tables(),
            'reserved_tables': restaurant.reserved_tables(),
            'cleaning_tables': restaurant.cleaning_tables(),
            'waiting_queue': restaurant.waiting_queue_count(),
            'tables': serializer.data
        })


class RestaurantCompareAPIView(APIView):
    def get(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        try:
            lat = float(request.GET.get('lat', get_default_coastal_coords()[0]))
            lon = float(request.GET.get('lon', get_default_coastal_coords()[1]))
            w_r = float(request.GET.get('w_r', 30))
            w_d = float(request.GET.get('w_d', 25))
            w_p = float(request.GET.get('w_p', 20))
            w_w = float(request.GET.get('w_w', 25))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid parameters'}, status=status.HTTP_400_BAD_REQUEST)

        score_data = calculate_waqt_score(
            restaurant, lat, lon,
            weight_rating=w_r, weight_distance=w_d, weight_price=w_p, weight_wait=w_w
        )
        return Response(score_data)
