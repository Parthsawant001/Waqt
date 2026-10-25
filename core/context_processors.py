from django.conf import settings

def waqt_context(request):
    return {
        'APP_NAME': 'Waqt',
        'APP_MARATHI': 'वेळ',
        'APP_TAGLINE': 'Know the table situation before you reach the restaurant.',
        'PILOT_REGION': 'Palghar × Virar Coastal Pilot',
        'user': request.user,
        'is_customer': request.user.is_authenticated and getattr(request.user, 'role', '') == 'CUSTOMER',
        'is_owner': request.user.is_authenticated and getattr(request.user, 'role', '') == 'OWNER',
    }
