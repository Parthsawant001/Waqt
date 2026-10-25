from django import forms
from .models import QueueEntry

class JoinQueueForm(forms.ModelForm):
    party_size = forms.IntegerField(
        min_value=1, max_value=20, initial=2,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 20})
    )

    class Meta:
        model = QueueEntry
        fields = ['party_size']
