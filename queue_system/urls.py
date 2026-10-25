from django.urls import path
from . import views, api_views

app_name = 'queue_system'

urlpatterns = [
    path('join/<slug:slug>/', views.join_queue_view, name='join'),
    path('<int:pk>/', views.queue_status_view, name='status'),
    path('<int:pk>/cancel/', views.cancel_queue_view, name='cancel'),
    
    # Live Polling API
    path('api/<int:pk>/status/', api_views.QueueStatusAPIView.as_view(), name='api_status'),
]
