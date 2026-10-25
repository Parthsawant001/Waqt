from django import forms
from .models import Restaurant, RestaurantTable, MenuItem, Review

class RestaurantTableForm(forms.ModelForm):
    class Meta:
        model = RestaurantTable
        fields = ['table_number', 'capacity', 'status']
        widgets = {
            'table_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 10 or A1'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 20}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['name', 'description', 'price', 'category', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Dish name'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Fresh catch preparation details...'}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.50'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices=[(i, f"{i} Stars") for i in range(5, 0, -1)], attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Share your coastal dining experience...'}),
        }


class RestaurantClaimForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Ramesh Patil'})
    )
    phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. +91 98230 12345'})
    )
    role_in_business = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Owner, Managing Partner, Head Chef'})
    )
    verification_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 4,
            'placeholder': 'Please state your association with the restaurant, FSSAI license number, GSTIN, business landline, or municipal license details to verify your claim...'
        })
    )
