import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import CustomUser, Bid 

class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        label="Password",
        help_text="Enter a strong password.",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password",
        help_text="Enter the same password as above for verification.",
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role']

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        # Check if passwords match
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields must match.")

        return cleaned_data

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1:
            # Validate password strength
            validate_password(password1)
        return password1

    def clean_role(self):
        role = self.cleaned_data.get('role')
        valid_roles = dict(CustomUser.USER_ROLE_CHOICES).keys()
        if role not in valid_roles:
            raise forms.ValidationError("Invalid role selected.")
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = ['item_name', 'item_description', 'starting_price', 'auction_end_time', 'image']
        widgets = {
            'auction_end_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'item_description': forms.Textarea(attrs={'rows': 4, 'cols': 50, 'class': 'form-control'}),
            'image': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Image URL'}),
        }

    def clean_auction_end_time(self):
        auction_end_time = self.cleaned_data.get('auction_end_time')
        if auction_end_time <= timezone.now():
            raise forms.ValidationError("Auction end time must be in the future.")
        return auction_end_time

class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(max_length=255)
    shipping_city = forms.CharField(max_length=100)
    shipping_postal_code = forms.CharField(max_length=20)
    shipping_country = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=20)

class ContactForm(forms.Form):
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
        label='First Name'
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
        label='Last Name'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        label='Email'
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your Message', 'rows': 4}),
        label='Message'
    )