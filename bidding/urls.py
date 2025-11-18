from django.urls import path
from . import views
from django.contrib.auth.views import PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

urlpatterns = [
    # Authentication Views
    # path('login/', views.CustomLoginView.as_view(), name='LogIn'),
    path('login/', views.CustomLoginView.as_view(), name='LogIn'),
    path('register/', views.RegisterPage.as_view(), name='Register'),
    path('logout/', views.CustomLogoutView.as_view(), name='LogOut'), 
    # path('notification/', views.NotificationListView.as_view(), name='notifications'), 
    # path('navigation/', views.NavigationView.as_view(), name='navigation'),

    # Password Reset Views
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('password_reset_done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Home
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('notifications/mark-read/<int:notification_id>/', views.MarkNotificationReadView.as_view(), name='mark_notification_read'),
    path('notifications/mark-all-read/', views.MarkAllNotificationsReadView.as_view(), name='mark_all_notifications_read'),

    # Bid Management
    path('bids/', views.BidListView.as_view(), name='bid_list'),
    path('bid/update/<int:pk>/', views.BidUpdateView.as_view(), name='update_bid'),
    path('delete/<int:bid_id>/', views.BidDeleteView.as_view(), name='delete_bid'),
    path('create-bid/', views.BidCreateView.as_view(), name='create_bid'),
    path('place-bid/<int:bid_id>/', views.PlaceBidView.as_view(), name='place_bid'),
    path('bid-detail/<int:bid_id>/', views.BidDetailView.as_view(), name='bid_detail'),

    # Dashboard Views
    path('admin-dashboard/', views.DashboardAdminView.as_view(), name='admin_dashboard'),
    path('seller-dashboard/', views.SellerDashboardView.as_view(), name='seller_dashboard'),
    path('bidder-dashboard/', views.BidderDashboardView.as_view(), name='bidder_dashboard'),

    path('checkout/<int:bid_id>/', views.CheckoutView.as_view(), name='checkout'),
    path('payment-success/<int:payment_id>/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('no-winning-bid/', views.NoWinningBidView.as_view(), name='no_winning_bid'),
    path('stripe/webhook/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
]
