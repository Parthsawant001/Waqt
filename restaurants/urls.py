from django.urls import path
from . import views, api_views

app_name = 'restaurants'

urlpatterns = [
    path('search/', views.restaurant_search_view, name='search'),
    path('compare/', views.restaurant_compare_view, name='compare'),
    path('<slug:slug>/claim/', views.claim_restaurant_view, name='claim'),
    path('<slug:slug>/', views.restaurant_detail_view, name='detail'),
    path('<slug:slug>/review/', views.add_review_view, name='add_review'),
    path('owner/kitchen/', views.owner_kitchen_display_view, name='owner_kitchen'),
    
    # REST API endpoints
    path('api/list/', api_views.RestaurantListAPIView.as_view(), name='api_list'),
    path('api/<int:restaurant_id>/live-tables/', api_views.LiveTableStatusAPIView.as_view(), name='api_live_tables'),
    path('api/<int:restaurant_id>/compare/', api_views.RestaurantCompareAPIView.as_view(), name='api_compare'),
]

from .owner_api import (
    OwnerDashboardAPIView, OwnerReservationActionAPIView, 
    OwnerQueueActionAPIView, OwnerTableStatusAPIView,
    OwnerMenuAPIView, OwnerMenuDetailAPIView,
    OwnerKitchenOrderAPIView, OwnerKitchenOrderDetailAPIView,
    OwnerTableAPIView, OwnerTableDetailAPIView
)

urlpatterns += [
    path('api/owner/dashboard/', OwnerDashboardAPIView.as_view(), name='api_owner_dashboard'),
    path('api/owner/tables/', OwnerTableAPIView.as_view(), name='api_owner_tables'),
    path('api/owner/tables/<int:pk>/', OwnerTableDetailAPIView.as_view(), name='api_owner_table_detail'),
    path('api/owner/reservations/<int:pk>/<str:action>/', OwnerReservationActionAPIView.as_view(), name='api_owner_reservation_action'),
    path('api/owner/queue/<int:pk>/<str:action>/', OwnerQueueActionAPIView.as_view(), name='api_owner_queue_action'),
    path('api/owner/tables/<int:pk>/status/', OwnerTableStatusAPIView.as_view(), name='api_owner_table_status'),
    path('api/owner/menu/', OwnerMenuAPIView.as_view(), name='api_owner_menu'),
    path('api/owner/menu/<int:pk>/', OwnerMenuDetailAPIView.as_view(), name='api_owner_menu_detail'),
    path('api/owner/kitchen/orders/', OwnerKitchenOrderAPIView.as_view(), name='api_owner_kitchen_orders'),
    path('api/owner/kitchen/orders/<int:pk>/', OwnerKitchenOrderDetailAPIView.as_view(), name='api_owner_kitchen_order_detail'),
]
