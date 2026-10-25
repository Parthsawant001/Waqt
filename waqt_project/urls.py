"""
waqt_project URL Configuration
Palghar–Virar Coastal Pilot
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from restaurants.views import (
    landing_index_view,
    owner_dashboard_view,
    owner_table_management_view,
    owner_menu_management_view,
    owner_kitchen_display_view,
)
from reservations.views import owner_reservation_management_view
from queue_system.views import owner_queue_management_view
from analytics.views import owner_analytics_view
from accounts.views import customer_dashboard_view

customer_patterns = ([
    path('dashboard/', customer_dashboard_view, name='dashboard'),
], 'customer')

owner_patterns = ([
    path('dashboard/', owner_dashboard_view, name='dashboard'),
    path('tables/', owner_table_management_view, name='tables'),
    path('menu/', owner_menu_management_view, name='menu'),
    path('queue/', owner_queue_management_view, name='queue'),
    path('reservations/', owner_reservation_management_view, name='reservations'),
    path('analytics/', owner_analytics_view, name='analytics'),
    path('kitchen/', owner_kitchen_display_view, name='kitchen'),
], 'owner')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Landing Page
    path('', landing_index_view, name='index'),
    
    # Core Domain Apps
    path('accounts/', include('accounts.urls')),
    path('restaurants/', include('restaurants.urls')),
    path('reservations/', include('reservations.urls')),
    path('queue/', include('queue_system.urls')),
    path('analytics/', include('analytics.urls')),
    
    # Namespaced routes
    path('customer/', include(customer_patterns, namespace='customer')),
    path('owner/', include(owner_patterns, namespace='owner')),
    
    # Direct Shortcuts (for backwards compatibility)
    path('customer/dashboard/', customer_dashboard_view, name='customer_dashboard'),
    path('owner/dashboard/', owner_dashboard_view, name='owner_dashboard'),
    path('owner/tables/', owner_table_management_view, name='owner_tables'),
    path('owner/menu/', owner_menu_management_view, name='owner_menu'),
    path('owner/queue/', owner_queue_management_view, name='owner_queue'),
    path('owner/reservations/', owner_reservation_management_view, name='owner_reservations'),
    path('owner/analytics/', owner_analytics_view, name='owner_analytics'),
    path('owner/kitchen/', owner_kitchen_display_view, name='owner_kitchen'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
