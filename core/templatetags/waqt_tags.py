from django import template

register = template.Library()

@register.filter
def get_range(value):
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter
def subtract(value, arg):
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def status_badge(status):
    classes = {
        'AVAILABLE': 'badge-available',
        'OCCUPIED': 'badge-occupied',
        'RESERVED': 'badge-reserved',
        'CLEANING': 'badge-cleaning',
        'WAITING': 'badge-waiting',
        'CALLED': 'badge-called',
        'SEATED': 'badge-seated',
        'COMPLETED': 'badge-completed',
        'CANCELLED': 'badge-cancelled',
        'CONFIRMED': 'badge-confirmed',
        'PENDING': 'badge-pending',
    }
    return classes.get(status, 'badge-default')
