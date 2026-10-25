from django.db import models
from django.conf import settings
from django.utils import timezone
from restaurants.models import Restaurant, RestaurantTable
from reservations.models import Reservation

class QueueEntry(models.Model):
    STATUS_CHOICES = (
        ('WAITING', 'Waiting in Queue'),
        ('CALLED', 'Table Ready / Called'),
        ('SEATED', 'Seated at Table'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled by Customer'),
        ('EXPIRED', 'Expired'),
        ('NO_SHOW', 'No Show'),
    )

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='queue_entries')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='queue_entries')
    party_size = models.PositiveIntegerField(default=2)
    position = models.PositiveIntegerField(default=1)
    estimated_wait_minutes = models.PositiveIntegerField(default=15)
    actual_wait_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Calculated upon being seated")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WAITING')
    joined_at = models.DateTimeField(default=timezone.now)
    called_at = models.DateTimeField(null=True, blank=True)
    seated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['joined_at']

    def __str__(self):
        return f"Queue #{self.position} - {self.customer.username} ({self.party_size}p) at {self.restaurant.name}"


class TableTurnover(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='turnovers')
    table = models.ForeignKey(RestaurantTable, on_delete=models.CASCADE, related_name='turnovers')
    reservation = models.ForeignKey(Reservation, on_delete=models.SET_NULL, null=True, blank=True, related_name='turnovers')
    party_size = models.PositiveIntegerField(default=2)
    occupied_at = models.DateTimeField()
    freed_at = models.DateTimeField()
    duration_minutes = models.FloatField(help_text="Actual turnover duration in minutes")

    class Meta:
        ordering = ['-freed_at']

    def __str__(self):
        return f"Turnover: {self.restaurant.name} Table {self.table.table_number} ({self.party_size}p) took {self.duration_minutes:.1f}m"
