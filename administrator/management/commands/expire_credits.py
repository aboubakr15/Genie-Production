from django.core.management.base import BaseCommand
from ai_agent.utils import expire_old_credits

class Command(BaseCommand):
    help = 'Checks for and expires credits that have passed their expiration date.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting credit expiration check...'))
        
        try:
            expired_amount = expire_old_credits()
            
            if expired_amount > 0:
                self.stdout.write(self.style.SUCCESS(f'Successfully expired {expired_amount} credits.'))
            else:
                self.stdout.write(self.style.SUCCESS('No credits needed expiration.'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error expiring credits: {str(e)}'))
