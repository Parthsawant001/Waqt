from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import QueueEntry
from core.services.wait_time_service import estimate_queue_wait_minutes

class QueueStatusAPIView(APIView):
    """
    Live Polling Endpoint for Customers:
    Called every 10-15s by customer vanilla JS frontend.
    Returns real-time position, parties ahead, updated wait estimate, and current status.
    """
    def get(self, request, pk):
        ticket = get_object_or_404(QueueEntry, pk=pk)
        parties_ahead = max(0, ticket.position - 1) if ticket.status == 'WAITING' else 0
        
        # Recalculate dynamic wait time if still waiting
        if ticket.status == 'WAITING':
            dynamic_wait = estimate_queue_wait_minutes(
                ticket.restaurant,
                ticket.party_size,
                queue_position=ticket.position
            )
            if dynamic_wait != ticket.estimated_wait_minutes:
                ticket.estimated_wait_minutes = dynamic_wait
                ticket.save(update_fields=['estimated_wait_minutes'])
        
        return Response({
            'ticket_id': ticket.id,
            'status': ticket.status,
            'status_display': ticket.get_status_display(),
            'position': ticket.position,
            'parties_ahead': parties_ahead,
            'estimated_wait_minutes': ticket.estimated_wait_minutes,
            'called_at': ticket.called_at.isoformat() if ticket.called_at else None,
            'is_called': ticket.status == 'CALLED',
            'is_seated': ticket.status == 'SEATED',
            'is_active': ticket.status in ['WAITING', 'CALLED'],
        })
