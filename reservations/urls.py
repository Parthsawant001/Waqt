from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('book/<slug:slug>/', views.book_table_view, name='book'),
    path('<int:pk>/', views.reservation_detail_view, name='detail'),
    path('<int:pk>/cancel/', views.cancel_reservation_view, name='cancel'),
]
