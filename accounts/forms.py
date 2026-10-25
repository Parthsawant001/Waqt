from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from restaurants.models import Restaurant
from restaurants.geocoding import geocode_address

User = get_user_model()

class CustomerRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'name@example.com'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98765 43210'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'CUSTOMER'
        if commit:
            user.save()
        return user


class OwnerRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Owner First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Owner Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'owner@restaurant.in'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 Restaurant Phone'}))

    # Restaurant Details
    restaurant_name = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Restaurant Name'}))
    cuisine_type = forms.CharField(max_length=120, required=True, initial='Koli Coastal Seafood', widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Traditional Koli Seafood'}))
    address = forms.CharField(max_length=500, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Street / Jetty Road Address'}))
    locality = forms.CharField(max_length=120, required=True, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Satpati, Kelva, Arnala, Vasai, Dahanu'}))
    price_range = forms.ChoiceField(choices=Restaurant.PRICE_CHOICES, initial='₹₹', widget=forms.Select(attrs={'class': 'form-select'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Tell diners about your coastal culinary heritage...'}), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'OWNER'
        if commit:
            user.save()
            # Geocode the address safely
            lat, lon, success = geocode_address(self.cleaned_data['address'], self.cleaned_data['locality'])
            Restaurant.objects.create(
                owner=user,
                name=self.cleaned_data['restaurant_name'],
                description=self.cleaned_data.get('description', ''),
                cuisine_type=self.cleaned_data['cuisine_type'],
                address=self.cleaned_data['address'],
                locality=self.cleaned_data['locality'],
                latitude=lat,
                longitude=lon,
                price_range=self.cleaned_data['price_range'],
                phone=self.cleaned_data['phone']
            )
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username or Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••'}))
