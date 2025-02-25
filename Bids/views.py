import stripe, json
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, TemplateView, View, FormView, UpdateView, CreateView
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.timezone import now
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Bid, BidItem, CustomUser, Notification, Payment
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import BidForm, CustomUserCreationForm, ContactForm, CheckoutForm
from django.core.mail import send_mail
from django.views import View
from django.urls import reverse
from django.conf import settings
# from django.utils.timezone import now
# from decimal import Decimal
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class CustomLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.user.is_authenticated:
            messages.success(self.request, "Successfully logged in!")
        return response

    def get_success_url(self):
        if self.request.user.is_authenticated:
            if not hasattr(self.request.user, 'role'):
                return reverse_lazy('LogIn')
            else:
                if self.request.user.role == "admin":
                    return reverse_lazy('admin_dashboard')
                if self.request.user.role == 'seller':
                    return reverse_lazy('seller_dashboard')
                elif self.request.user.role == 'bidder':
                    return reverse_lazy('bidder_dashboard')
        return reverse_lazy('home')

class RegisterPage(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home') 
        form = CustomUserCreationForm()
        return render(request, 'register.html', {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful!")

            # Redirect based on the user's role
            if user.role == 'seller':
                return redirect('seller_dashboard')
            elif user.role == 'bidder':
                return redirect('bidder_dashboard')

        # If form is invalid, re-render the form with errors
        return render(request, 'register.html', {'form': form})

class CustomLogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('LogIn')

class NotificationListView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        # Fetch unread notifications for the current user
        notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
        notification_list = [
            {
                'id': notification.id,
                'message': notification.message,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for notification in notifications
        ]

        return JsonResponse({
            'unread_count': notifications.count(),
            'notifications': notification_list,
        })

class NavigationView(ListView):
    model = Notification
    template_name = 'navigation.html'
    # context_object_name = 'notification'

    def get_queryset(self):
        request = self.request.user
        return Notification.objects.filter(user_id=request.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        request = self.request.user

        notifications = Notification.objects.filter(user_id=request.id)
        context['notifications'] = notifications
        return context

class HomeView(ListView):
    model = Bid
    template_name = 'index.html'
    # context_object_name = 'items'

    def get_queryset(self):
        # Return the queryset of Bid objects
        return Bid.objects.filter(auction_end_time__gt=timezone.now())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request.user
        notifications = Notification.objects.filter(user_id=request.id)
        context['notifications'] = notifications
        bids = Bid.objects.filter(auction_end_time__gt=timezone.now())
        context['bids'] = bids

        return context

class PasswordResetRequestView(View):
    def get(self, request):
        form = PasswordResetForm()
        return render(request, 'password_reset.html', {'form': form})

    def post(self, request):
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            associated_users = CustomUser.objects.filter(email=email)

            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Requested"
                    email_template_name = "password_reset_email.txt"
                    domain = get_current_site(request).domain
                    context = {
                        "email": user.email,
                        'domain': domain,
                        'site_name': 'AuctionSite',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "token": default_token_generator.make_token(user),
                        "username": user.username,
                    }
                    email_content = render_to_string(email_template_name, context)

                    try:
                        send_mail(subject, email_content, 'your_email@example.com', [user.email], fail_silently=False)
                    except Exception as e:
                        messages.error(request, f"Error sending email: {str(e)}")
                        return render(request, 'password_reset.html', {'form': form})

                messages.success(request, "Password reset email sent successfully!")
                return redirect("password_reset_done")
            else:
                messages.error(request, "No user is associated with this email address.")

        return render(request, 'password_reset.html', {'form': form})

class AboutView(TemplateView):
    template_name = 'about.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request.user
        notifications = Notification.objects.filter(user_id=request.id)
        context['notifications'] = notifications
        return context

class BidCreateView(LoginRequiredMixin,CreateView):
    model = Bid
    form_class = BidForm
    template_name = 'create_bid.html'
    success_url = reverse_lazy('bid_list')  
    def form_valid(self, form):
        form.instance.user = self.request.user 
        return super().form_valid(form)

class BidUpdateView(LoginRequiredMixin, UpdateView):
    model = Bid
    form_class = BidForm
    template_name = 'update_bid.html'
    context_object_name = 'bid'

    def get_success_url(self):
        messages.success(self.request, 'Bid updated successfully!')
        return reverse_lazy('bid_list')

    def form_valid(self, form):
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'There was an error updating the bid. Please check the form.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bid = self.get_object() 
        context['bid'] = bid 
        return context

class BidDeleteView(LoginRequiredMixin,View):
    def post(self, request, bid_id):
        bid = get_object_or_404(Bid, pk=bid_id)
        if bid.user_id == request.user.id:
            bid.delete()
            messages.success(request, "Bid has been successfully deleted.")
        else:
            messages.error(request, "You are not authorized to delete this bid.")
        return redirect('bid_list')

class BidDetailView(View):
    def get(self, request, bid_id):
        bid = get_object_or_404(Bid, pk=bid_id)
        return render(request, 'bid_detail.html', {'bid': bid})


class BidListView(LoginRequiredMixin, ListView):
    model = Bid
    template_name = 'bids_list.html'
    # context_object_name = 'bids'

    def get_queryset(self):
        """Filter out completed auctions."""
        return Bid.objects.filter(auction_end_time__gt=timezone.now() )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request.user
        notifications = Notification.objects.filter(user_id=request.id)
        context['notifications'] = notifications
        bids = Bid.objects.filter(auction_end_time__gt=timezone.now())
        context['bids'] = bids

        return context


class PlaceBidView(LoginRequiredMixin, View):
    def get(self, request, bid_id):
        bid = get_object_or_404(Bid, pk=bid_id)

        if bid.is_completed():
            messages.error(request, 'This auction has ended. You cannot place a bid.')
            return redirect('bid_list')

        return render(request, 'bids_list.html', {'bid': bid})

    def post(self, request, bid_id):
        bid = get_object_or_404(Bid, pk=bid_id)

        # Prevent bidding on completed auctions
        if bid.is_completed():
            messages.error(request, 'This auction has ended. You cannot place a bid.')
            return redirect('bid_list')

        bid_amount = request.POST.get('bid_amount')

        # Validate bid amount
        try:
            bid_amount = float(bid_amount)
        except ValueError:
            messages.error(request, 'Invalid bid amount.')
            return redirect('place_bid', bid_id=bid_id)

        if bid_amount < bid.starting_price:
            messages.error(request, 'Your bid must be higher than the starting price.')
            return redirect('place_bid', bid_id=bid_id)

        # Prevent duplicate bidding
        if BidItem.objects.filter(bid=bid, bidder_id=request.user.id).exists():
            messages.error(request, 'You have already placed a bid for this item.')
            return redirect('place_bid', bid_id=bid_id)

        # Save the bid
        new_bid_item = BidItem.objects.create(bid=bid, bidder=request.user, bid_amount=bid_amount)

        # Update the highest bid if necessary
        bid.update_highest_bid(bid_amount)

        # Check if the new bid is the highest and create a notification
        if new_bid_item.is_highest_bid():
            Notification.objects.create(
                user=request.user,
                message=f"You won the bid for '{bid.item_name}' with an amount of ${bid_amount}!"
            )

        messages.success(request, 'Your bid has been placed successfully!')
        return redirect('bid_list')

class ContactView(FormView):
    template_name = 'contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('contact_thank_you')

    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            request = self.request.user
            notifications = Notification.objects.filter(user_id=request.id)
            context['notifications'] = notifications
            return context

    def form_valid(self, form):        
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']
        email = form.cleaned_data['email']
        message = form.cleaned_data['message']

        send_mail(
            subject=f'Contact Form Submission from {first_name} {last_name}',
            message=message,
            from_email=email,
            recipient_list=['your_email@example.com'],
            fail_silently=False,
        )

        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)


class DashboardAdminView(LoginRequiredMixin,TemplateView):
    template_name = 'admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['sellers_count'] = CustomUser.objects.filter(role='seller').count()
        context['bidders_count'] = CustomUser.objects.filter(role='bidder').count()
        context['total_bids'] = Bid.objects.count()

        # Get all bids with the required fields
        context['bids'] = Bid.objects.all()

        # Get all users with their username, email, and role
        context['users'] = CustomUser.objects.all()

        return context


class SellerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'seller_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['seller_profile'] = self.request.user
        # Fetch the bids created by the current seller
        context['bids_list'] = Bid.objects.filter(user=self.request.user)
        return context

class BidderDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'bidder_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notifications = Notification.objects.filter(user_id=self.request.user.id)
        context['notifications'] = notifications
        context['bidder_profile'] = self.request.user
        context['now'] = timezone.now()  # Pass current time to the template

        bid_items = BidItem.objects.filter(bidder_id=self.request.user.id).select_related('bid')

        # Add bid and item details to context
        bids_placed = []
        for bid_item in bid_items:
            # Check if there is a completed payment for this bid
            payment = Payment.objects.filter(bid=bid_item.bid, user=self.request.user, payment_status='completed').first()

            # Corrected query to get the highest bid
            highest_bid = Bid.objects.filter(bid_items__bid=bid_item.bid).order_by('-total_bid_amount').first()

            bids_placed.append({
                'bid': bid_item.bid,
                'item': bid_item.bid.item_name,  # Correct field for item name
                'bid_id': bid_item.bid.id,
                'bid_amount': bid_item.bid_amount,
                'is_highest_bid': bid_item.bid == highest_bid,
                'payment_completed': payment is not None,  # Check if payment is completed
            })

        context['bids_placed'] = bids_placed
        return context

class NoWinningBidView(TemplateView):
    template_name = 'no_winning_bid.html'

stripe.api_key = settings.STRIPE_SECRET_KEY

class CheckoutView(View):
    def get(self, request, bid_id):
        # Retrieve the bid item
        bid = get_object_or_404(Bid, id=bid_id)

        # Retrieve the highest bid item
        highest_bid_item = BidItem.objects.filter(bid=bid).order_by('-bid_amount').first()
        if not highest_bid_item or highest_bid_item.bidder != request.user:
            return HttpResponse("You are not the highest bidder", status=403)

        # Prepare the form
        form = CheckoutForm()

        return render(request, 'checkout.html', {
            'form': form,
            'bid': bid,
            'highest_bid_item': highest_bid_item,
            'highest_bid_amount': highest_bid_item.bid_amount,  # Include this for clarity
        })

    def post(self, request, bid_id):
        # Retrieve the bid and highest bid item
        bid = get_object_or_404(Bid, id=bid_id)
        highest_bid_item = BidItem.objects.filter(bid=bid).order_by('-bid_amount').first()
        if not highest_bid_item or highest_bid_item.bidder != request.user:
            return HttpResponse("You are not the highest bidder", status=403)

        # Validate the form
        form = CheckoutForm(request.POST)
        if not form.is_valid():
            return render(request, 'checkout.html', {'form': form, 'bid': bid, 'highest_bid_item': highest_bid_item})

        # Extract form data
        shipping_address = form.cleaned_data['shipping_address']
        shipping_city = form.cleaned_data['shipping_city']
        shipping_postal_code = form.cleaned_data['shipping_postal_code']
        shipping_country = form.cleaned_data['shipping_country']
        email = form.cleaned_data['email']
        phone_number = form.cleaned_data['phone_number']

        # Create payment record
        payment = Payment.objects.create(
            bid=bid,
            user=request.user,
            amount=highest_bid_item.bid_amount,
            payment_status='pending',
            payment_method=None,  # Will be set after Stripe payment
            payment_reference=None,
        )

        # Create Stripe checkout session
        session = self.create_stripe_checkout_session(request, bid, highest_bid_item.bid_amount, payment.id)
        if session:
            return redirect(session.url)
        else:
            return HttpResponse("Error creating Stripe checkout session", status=500)

    def create_stripe_checkout_session(self, request, bid, bid_amount, payment_id):
        line_items = [{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': bid.item_name},
                'unit_amount': int(bid_amount * 100),
            },
            'quantity': 1,
        }]
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=request.build_absolute_uri(reverse('payment_success', args=[payment_id])) + '?session_id={CHECKOUT_SESSION_ID}',
                metadata={'payment_id': payment_id},
            )
            return session
        except stripe.error.StripeError as e:
            print(f"Stripe error: {e}")
            return None

class PaymentSuccessView(View):
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)
        payment.mark_completed()  # Update the payment status
        return render(request, 'payment_success.html', {'payment': payment})

class StripeWebhookView(View):
    @method_decorator(csrf_exempt)
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except ValueError as e:
            logger.error(f"Invalid payload: {str(e)}")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            return HttpResponse(status=400)

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            payment_intent = stripe.PaymentIntent.retrieve(session['payment_intent'])
            receipt_url = payment_intent.get('charges', {}).get('data', [{}])[0].get('receipt_url')

            # Assuming the client_reference_id is used to store the bid ID
            bid_id = session['client_reference_id']
            try:
                bid = Bid.objects.get(id=bid_id)
                # Create a new Payment record
                payment = Payment.objects.create(
                    bid=bid,
                    user=bid.user,  # Assuming the user is the one who placed the bid
                    amount=session['amount_total'] / 100,  # Convert from cents to dollars
                    payment_status='completed',
                    payment_method='Stripe',
                    payment_reference=session['id'],  # Stripe session ID
                    shipping_address=session.get('shipping', {}).get('address', {}).get('line1', ''),
                    shipping_city=session.get('shipping', {}).get('address', {}).get('city', ''),
                    shipping_postal_code=session.get('shipping', {}).get('address', {}).get('postal_code', ''),
                    shipping_country=session.get('shipping', {}).get('address', {}).get('country', ''),
                    email=session.get('customer_email', ''),
                    phone_number=session.get('phone_number', '')
                )
                logger.info(f"Payment for bid {bid.id} created successfully with reference {payment.payment_reference}.")
                
                # Optionally, you can also update the bid status or any other related logic here
                # For example, if you want to mark the bid as completed:
                # bid.update_highest_bid(payment.amount)  # If you want to update the highest bid
            except Bid.DoesNotExist:
                logger.error(f"Bid {bid_id} not found for session {session.id}")

        return HttpResponse(status=200)
