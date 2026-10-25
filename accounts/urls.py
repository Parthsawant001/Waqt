from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/customer/', views.customer_register_view, name='customer_register'),
    path('signup/owner/', views.owner_register_view, name='owner_register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_router_view, name='dashboard'),
]
