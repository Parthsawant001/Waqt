import re

with open('queue_system/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

queue_status_old = """    STATUS_CHOICES = (
        ('WAITING', 'Waiting in Queue'),
        ('CALLED', 'Table Ready / Called'),
        ('SEATED', 'Seated at Table'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled by Customer'),
        ('EXPIRED', 'Expired / No Show'),
    )"""

queue_status_new = """    STATUS_CHOICES = (
        ('WAITING', 'Waiting in Queue'),
        ('CALLED', 'Table Ready / Called'),
        ('SEATED', 'Seated at Table'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled by Customer'),
        ('EXPIRED', 'Expired'),
        ('NO_SHOW', 'No Show'),
    )"""

content = content.replace(queue_status_old, queue_status_new)

if 'actual_wait_minutes =' not in content:
    # insert actual_wait_minutes after estimated_wait_minutes
    content = content.replace('estimated_wait_minutes = models.PositiveIntegerField(default=15)',
                              'estimated_wait_minutes = models.PositiveIntegerField(default=15)\n    actual_wait_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Calculated upon being seated")')

with open('queue_system/models.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated queue_system/models.py")
