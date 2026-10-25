from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from .models import Restaurant, RestaurantTable, MenuItem, KitchenOrder
from queue_system.models import QueueEntry
from reservations.models import Reservation
from .owner_serializers import (
    OwnerTableSerializer, OwnerMenuSerializer, 
    KitchenOrderSerializer, OwnerQueueSerializer, OwnerReservationSerializer
)
from core.services.allocation_service import reserve_table_greedily
from core.services.queue_service import call_next_eligible_party

class OwnerBaseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_restaurant(self, request):
        return Restaurant.objects.filter(owner=request.user).first()

class OwnerDashboardAPIView(OwnerBaseAPIView):
    def get(self, request):
        restaurant = self.get_restaurant(request)
        if not restaurant:
            return Response({'error': 'Not an owner'}, status=403)

        today = timezone.now().date()
        
        # Today's metrics
        todays_reservations = Reservation.objects.filter(restaurant=restaurant, reservation_date=today)
        waiting_queue = QueueEntry.objects.filter(restaurant=restaurant, status='WAITING')
        kitchen_orders = KitchenOrder.objects.filter(restaurant=restaurant).exclude(status__in=['COMPLETED', 'CANCELLED'])

        # Data serialization
        data = {
            'restaurant_name': restaurant.name,
            'metrics': {
                'total_reservations': todays_reservations.count(),
                'checked_in': todays_reservations.filter(status='CHECKED_IN').count(),
                'available_tables': restaurant.available_tables(),
                'occupied_tables': restaurant.occupied_tables(),
                'waiting_queue': waiting_queue.count(),
                'kitchen_pending': kitchen_orders.filter(status='NEW').count(),
                'kitchen_preparing': kitchen_orders.filter(status='PREPARING').count(),
                'kitchen_ready': kitchen_orders.filter(status='READY').count(),
            },
            'tables': OwnerTableSerializer(restaurant.tables.all(), many=True).data,
            'queue': OwnerQueueSerializer(waiting_queue, many=True).data,
            'reservations': OwnerReservationSerializer(todays_reservations, many=True).data,
            'kitchen_orders': KitchenOrderSerializer(kitchen_orders, many=True).data
        }
        return Response(data)

class OwnerReservationActionAPIView(OwnerBaseAPIView):
    def post(self, request, pk, action):
        restaurant = self.get_restaurant(request)
        reservation = get_object_or_404(Reservation, id=pk, restaurant=restaurant)

        if action == 'check-in':
            if reservation.status != 'CONFIRMED':
                return Response({'error': 'Can only check in confirmed reservations'}, status=400)
            
            # RUN TABLE ALLOCATION ALGORITHM
            table = reserve_table_greedily(restaurant, reservation.party_size, reservation=reservation)
            if table:
                reservation.status = 'CHECKED_IN'
                reservation.checked_in_at = timezone.now()
                reservation.save()
                
                # Table status is already RESERVED by reserve_table_greedily. Update to OCCUPIED.
                table.status = 'OCCUPIED'
                table.save()
                return Response({'status': 'success', 'table_number': table.table_number})
            else:
                return Response({'error': 'No suitable table available right now.'}, status=400)
                
        elif action == 'complete':
            reservation.status = 'COMPLETED'
            reservation.completed_at = timezone.now()
            reservation.save()
            if reservation.table:
                reservation.table.status = 'CLEANING'
                reservation.table.save()
            return Response({'status': 'success'})

        return Response({'error': 'Invalid action'}, status=400)

class OwnerQueueActionAPIView(OwnerBaseAPIView):
    def post(self, request, pk, action):
        restaurant = self.get_restaurant(request)
        entry = get_object_or_404(QueueEntry, id=pk, restaurant=restaurant)

        if action == 'call':
            entry.status = 'CALLED'
            entry.called_at = timezone.now()
            entry.save()
            return Response({'status': 'success'})
        elif action == 'seat':
            # Assign table if provided
            table_id = request.data.get('table_id')
            if table_id:
                table = get_object_or_404(RestaurantTable, id=table_id, restaurant=restaurant)
                table.status = 'OCCUPIED'
                table.save()
            
            entry.status = 'SEATED'
            entry.seated_at = timezone.now()
            # Calculate actual wait time
            duration = (entry.seated_at - entry.joined_at).total_seconds() / 60.0
            entry.actual_wait_minutes = int(round(duration))
            entry.save()
            return Response({'status': 'success'})
        elif action == 'cancel':
            entry.status = 'CANCELLED'
            entry.save()
            return Response({'status': 'success'})
        
        return Response({'error': 'Invalid action'}, status=400)

class OwnerTableStatusAPIView(OwnerBaseAPIView):
    def post(self, request, pk):
        restaurant = self.get_restaurant(request)
        table = get_object_or_404(RestaurantTable, id=pk, restaurant=restaurant)
        
        new_status = request.data.get('status')
        if new_status in dict(RestaurantTable.STATUS_CHOICES):
            table.status = new_status
            table.save()
            
            # Table Status -> Queue Automation Check
            if new_status == 'AVAILABLE':
                called = call_next_eligible_party(restaurant, table)
                if called:
                    return Response({'status': 'success', 'called_party': called.id})
                    
            return Response({'status': 'success'})
        return Response({'error': 'Invalid status'}, status=400)

from rest_framework import generics

class OwnerMenuAPIView(generics.ListCreateAPIView):
    serializer_class = OwnerMenuSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_serializer_class().Meta.model.objects.filter(restaurant__owner=self.request.user)

    def perform_create(self, serializer):
        restaurant = Restaurant.objects.filter(owner=self.request.user).first()
        if restaurant:
            serializer.save(restaurant=restaurant)

class OwnerMenuDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OwnerMenuSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_serializer_class().Meta.model.objects.filter(restaurant__owner=self.request.user)

class OwnerKitchenOrderAPIView(generics.ListCreateAPIView):
    serializer_class = KitchenOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_serializer_class().Meta.model.objects.filter(restaurant__owner=self.request.user)

    def perform_create(self, serializer):
        restaurant = Restaurant.objects.filter(owner=self.request.user).first()
        if restaurant:
            serializer.save(restaurant=restaurant)

class OwnerKitchenOrderDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = KitchenOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_serializer_class().Meta.model.objects.filter(restaurant__owner=self.request.user)

class OwnerTableAPIView(generics.ListCreateAPIView):
    serializer_class = OwnerTableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_serializer_class().Meta.model.objects.filter(restaurant__owner=self.request.user)

    def perform_create(self, serializer):
        restaurant = Restaurant.objects.filter(owner=self.request.user).first()
        if restaurant:
            serializer.save(restaurant=restaurant)

class OwnerTableDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OwnerTableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.get_serializer_class().Meta.model.objects.filter(restaurant__owner=self.request.user)
