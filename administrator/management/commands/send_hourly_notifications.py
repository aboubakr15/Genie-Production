from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import LeadTerminationCode, Notification, UserLeader, TerminationCode, TaskLog
import logging
from datetime import timedelta

logger = logging.getLogger('custom')

class Command(BaseCommand):
    help = 'Send notifications for callbacks due in the next hour'

    def handle(self, *args, **options):
        now = timezone.now()
        one_hour_later = now + timedelta(hours=1)
        
        # Log start
        self.stdout.write(self.style.SUCCESS(f'Checking for callbacks between {now} and {one_hour_later}'))

        # Find leads with CB_date in the next hour
        flags = TerminationCode.objects.filter(name__in=['CB', 'PR']).all()
        leads_with_cb = LeadTerminationCode.objects.filter(
            CB_date__range=(now, one_hour_later),
            flag__in=flags
        )

        count = 0
        for lead_termination in leads_with_cb:
            user = lead_termination.user
            lead = lead_termination.lead
            show = lead_termination.sales_show

            try:
                # Notify the Agent/Target User
                message = f"Reminder: Call due within 1 hour for lead '{lead.name}' in show '{show.name}'."
                Notification.objects.create(
                    sender=user, # System notification, but using user as sender is common pattern here or use admin
                    receiver=user,
                    message=message,
                    notification_type=5 # Callback type
                )

                # Notify the Team Leader
                try:
                    user_leader = UserLeader.objects.get(user=user).leader
                    leader_message = f"Team Member {user.username} has a call due in 1 hour for lead '{lead.name}'."
                    Notification.objects.create(
                        sender=user,
                        receiver=user_leader,
                        message=leader_message,
                        notification_type=5
                    )
                except UserLeader.DoesNotExist:
                    pass

                count += 1
                
            except Exception as e:
                logger.error(f"Error processing callback notification for lead {lead.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f'Successfully sent {count} callback notifications.'))
