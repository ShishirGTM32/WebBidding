from django.core.management.base import BaseCommand
from django.utils import timezone
from bidding.models import Bid, BidItem, Notification

class Command(BaseCommand):
    help = 'Check for ended auctions and notify winners'

    def handle(self, *args, **kwargs):
        ended_bids = Bid.objects.filter(
            auction_end_time__lte=timezone.now(),
            is_auction_ended=False  
        )

        for bid in ended_bids:

            highest_bid_item = BidItem.objects.filter(bid=bid).order_by('-bid_amount').first()
            
            if highest_bid_item:
                Notification.objects.create(
                    user=highest_bid_item.bidder,
                    message=f"Congratulations! You won the auction for '{bid.item_name}' with a bid of ${highest_bid_item.bid_amount}. Please proceed to checkout.",
                    is_read=False
                )
                
                other_bidders = BidItem.objects.filter(bid=bid).exclude(id=highest_bid_item.id)
                for bid_item in other_bidders:
                    Notification.objects.create(
                        user=bid_item.bidder,
                        message=f"The auction for '{bid.item_name}' has ended. Unfortunately, you were not the highest bidder.",
                        is_read=False
                    )
                
                self.stdout.write(self.success_message(f'Processed auction: {bid.item_name}'))
            bid.is_auction_ended = True
            bid.save()