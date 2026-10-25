from django import forms
from datetime import date
from .models import Reservation

class ReservationBookingForm(forms.ModelForm):
    party_size = forms.IntegerField(
        min_value=1, max_value=20, initial=2,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 20})
    )
    reservation_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        initial=date.today
    )
    reservation_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'})
    )
    special_requests = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Sea-facing preference, dietary requirements, celebrations...'})
    )

    class Meta:
        model = Reservation
        fields = ['party_size', 'reservation_date', 'reservation_time', 'special_requests']

    def clean_reservation_date(self):
        res_date = self.cleaned_data['reservation_date']
        if res_date < date.today():
            raise forms.ValidationError("Reservation date cannot be in the past.")
        return res_date
