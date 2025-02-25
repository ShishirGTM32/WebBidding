from django.db import models
from django.contrib.auth.models import AbstractBaseUser , BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.timezone import now

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password, role, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not username:
            raise ValueError('The Username field must be set')
        if role not in ['bidder', 'seller']:
            raise ValueError('Invalid role specified')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, role='admin', **extra_fields)

    def create_bidder(self, username, email, password, **extra_fields):
        user = self.create_user(username, email, password, role='bidder', **extra_fields)
        BidderProfile.objects.create(user=user)
        return user

    def create_seller(self, username, email, password, **extra_fields):
        user = self.create_user(username, email, password, role='seller', **extra_fields)
        SellerProfile.objects.create(user=user)
        return user


class CustomUser(AbstractBaseUser , PermissionsMixin):
    USER_ROLE_CHOICES = (
        ('bidder', 'Bidder'),
        ('seller', 'Seller'),
    )

    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=USER_ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()  # Use CustomUser Manager

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'role']

    def __str__(self):
        return self.username


class BidderProfile(models.Model):
    user = models.OneToOneField(CustomUser , on_delete=models.CASCADE, related_name='bidder_profile')
    additional_bidder_field = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Bidder Profile for {self.user.username}"


class SellerProfile(models.Model):
    user = models.OneToOneField(CustomUser , on_delete=models.CASCADE, related_name='seller_profile')
    additional_seller_field = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Seller Profile for {self.user.username}"


class Bid(models.Model):
    user = models.ForeignKey(CustomUser , on_delete=models.SET_NULL, null=True, blank=True)  # Use CustomUser 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_bid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    item_name = models.CharField(max_length=255)
    item_description = models.TextField()
    starting_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    highest_bid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    auction_end_time = models.DateTimeField()
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    image = models.URLField(max_length=200, null=True, blank=True)

    def is_completed(self):
        """Check if the auction has ended."""
        return timezone.now() > self.auction_end_time

    def update_highest_bid(self, bid_amount):
        """Update the highest bid if the new bid is higher."""
        if self.highest_bid is None or bid_amount > self.highest_bid:
            self.highest_bid = bid_amount
            self.save()

    def __str__(self):
        return f"Bid #{self.id} for {self.item_name} by {self.user}"


class BidItem(models.Model):
    bid = models.ForeignKey(Bid, related_name='bid_items', on_delete=models.CASCADE)
    bidder = models.ForeignKey(CustomUser , on_delete=models.SET_NULL, null=True, blank=True)  # Use CustomUser 
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bid_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bid by {self.bidder} - {self.bid_amount}"

    def is_highest_bid(self):
        """Check if this bid is the highest bid."""
        return self.bid.bid_items.filter(bid_amount__gt=self.bid_amount).count() == 0

    def create_notification_if_winner(self):
        """Create a notification if this bid is the highest bid."""
        if self.is_highest_bid():
            Notification.objects.create(
                user=self.bidder,
                message=f"You won the bid for '{self.bid.item_name}' with an amount of ${self.bid_amount}!",
            )


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    bid = models.ForeignKey(Bid, related_name='payments', on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser , on_delete=models.CASCADE)  # Use CustomUser 
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=100, blank=True, null=True)
    payment_reference = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    transaction_date = models.DateTimeField(null=True, blank=True)
    
    # Shipping details
    shipping_address = models.CharField(max_length=255, null=True)
    shipping_city = models.CharField(max_length=100, null=True)
    shipping_postal_code = models.CharField(max_length=20, null=True)
    shipping_country = models.CharField(max_length=100, null=True)
    email = models.EmailField(null=True)
    phone_number = models.CharField(max_length=20, null=True)

    def __str__(self):
        return f"Payment for {self.bid.item_name} by {self.user.username}"

    def is_successful(self):
        return self.payment_status == 'completed'

    def is_failed(self):
        return self.payment_status == 'failed'

    def is_pending(self):
        return self.payment_status == 'pending'

    def is_refunded(self):
        return self.payment_status == 'refunded'

    def mark_completed(self):
        self.payment_status = 'completed'
        self.transaction_date = now()
        self.save()

    def mark_failed(self):
        self.payment_status = 'failed'
        self.save()

    def mark_refunded(self):
        self.payment_status = 'refunded'
        self.save()


class Contact(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.email})'


class Notification(models.Model):
    user = models.ForeignKey(CustomUser  , on_delete=models.CASCADE)  # Use CustomUser  
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Notification for {self.user.username}"

    def is_due(self):
        return self.due_date and timezone.now() > self.due_date