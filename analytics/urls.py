from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('owner/', views.owner_analytics_view, name='owner_analytics'),
]
