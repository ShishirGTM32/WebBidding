from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Bid, BidItem, Notification

def check_and_notify_auction_end():
    """Check for ended auctions and notify winners"""
    ended_bids = Bid.objects.filter(
        auction_end_time__lte=timezone.now(),
        is_auction_ended=False
    )

    for bid in ended_bids:
        # Get the highest bidder
        highest_bid_item = BidItem.objects.filter(bid=bid).order_by('-bid_amount').first()
        
        if highest_bid_item:
            # Create notification for the winner
            Notification.objects.get_or_create(
                user=highest_bid_item.bidder,
                message=f"Congratulations! You won the auction for '{bid.item_name}' with a bid of ${highest_bid_item.bid_amount}. Please proceed to checkout.",
                defaults={'is_read': False}
            )
            
            # Notify seller
            Notification.objects.get_or_create(
                user=bid.user,
                message=f"Your auction for '{bid.item_name}' has ended. Winner: {highest_bid_item.bidder.username} with ${highest_bid_item.bid_amount}",
                defaults={'is_read': False}
            )
            
            # Notify other bidders they didn't win
            other_bidders = BidItem.objects.filter(bid=bid).exclude(id=highest_bid_item.id)
            for bid_item in other_bidders:
                Notification.objects.get_or_create(
                    user=bid_item.bidder,
                    message=f"The auction for '{bid.item_name}' has ended. The winning bid was ${highest_bid_item.bid_amount}.",
                    defaults={'is_read': False}
                )
        
        # Mark the auction as processed
        bid.is_auction_ended = True
        bid.save()