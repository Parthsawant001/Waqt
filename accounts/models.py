from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('CUSTOMER', 'Customer'),
        ('OWNER', 'Restaurant Owner'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CUSTOMER')
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_owner(self):
        return self.role == 'OWNER'

    def is_customer(self):
        return self.role == 'CUSTOMER'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
