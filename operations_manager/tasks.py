from celery import shared_task
from django.shortcuts import get_object_or_404
from django.utils import timezone
from main.models import (
    ReadyShow, SalesShow, LeadTerminationHistory, Referral,
    LeadPhoneNumbers, Notification, User
)
from main.utils import send_websocket_message, NOTIFICATIONS_STATES

@shared_task
def cut_ready_show_into_sales_shows_task(ready_show_id, user_id):
    user = None
    try:
        user = User.objects.get(id=user_id)
        # Get the ReadyShow and mark it as done
        ready_show = ReadyShow.objects.get(id=ready_show_id)
        ready_show.is_done = True
        ready_show.done_date = timezone.now()
        ready_show.save()

        # Array to Hold Referrals
        leads_to_referral = []

        # Labels to handle separately
        special_labels = ['europe', 'asia', 'uk']

        # Check if the ReadyShow has a special label
        if ready_show.label.lower() in special_labels:
            # Get all leads for the special label
            all_leads = list(ready_show.leads.all())
            
            # Filter out leads that match the termination condition
            leads = []
            
            for lead in all_leads:
                if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name__in=['show', 'CD']).exists():
                    if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name='CD').exists():
                        leads_to_referral.append(lead)
                    continue
                leads.append(lead)
            
            total_leads = len(leads)

            # Determine the number of SalesShows needed based on the number of leads
            if total_leads <= 20:
                sales_shows_count = 1
            elif 20 < total_leads <= 50:
                sales_shows_count = 2
            elif 50 < total_leads <= 100:
                sales_shows_count = 4
            elif 100 < total_leads <= 200:
                sales_shows_count = 8
            elif 200 < total_leads <= 400:
                sales_shows_count = 16
            elif 400 < total_leads <= 800:
                sales_shows_count = 32
            elif 800 < total_leads <= 1600:
                sales_shows_count = 64
            else:
                sales_shows_count = total_leads // 100  # Continuing the pattern (dividing by 100 for very large groups)

            # Create empty lists for each SalesShow to hold leads
            sales_show_leads = [[] for _ in range(sales_shows_count)]

            # Split leads evenly among the SalesShow objects
            split_size = total_leads // sales_shows_count

            for i in range(sales_shows_count):
                start_index = i * split_size
                end_index = start_index + split_size
                sales_show_leads[i].extend(leads[start_index:end_index])

            # Handle leftover leads (if any)
            leftover_leads = leads[sales_shows_count * split_size:]
            for i, lead in enumerate(leftover_leads):
                sales_show_leads[i % sales_shows_count].append(lead)

            # Create SalesShows and assign the leads to them
            for idx, leads_chunk in enumerate(sales_show_leads, start=1):
                sales_show_name = f"{ready_show.sheet.name} ({ready_show.label.upper()} {idx})"  # Append number and label to SalesShow name
                sales_show = SalesShow.objects.create(
                    name=sales_show_name,
                    sheet=ready_show.sheet,
                    is_done=False,
                    label=ready_show.label
                )
                sales_show.leads.add(*leads_chunk)
                sales_show.save()

        else:
            # For non-special labels, we need to determine time zones from phone numbers
            time_zones = ['cen', 'est', 'pac']
            
            # Prefetch phone numbers with time zones for all leads
            from django.db.models import Prefetch
            phone_numbers_prefetch = Prefetch(
                'leadphonenumbers_set',
                queryset=LeadPhoneNumbers.objects.filter(sheet=ready_show.sheet),
                to_attr='phone_numbers'
            )
            all_leads = ready_show.leads.prefetch_related(phone_numbers_prefetch).all()
            
            # Group leads by time zone based on their phone numbers
            leads_by_zone = {tz: [] for tz in time_zones}
            
            for lead in all_leads:
                # Check termination first
                if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name__in=['show', 'CD']).exists():
                    if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name='CD').exists():
                        leads_to_referral.append(lead)
                    continue
                
                # Determine time zone from phone numbers
                time_zone = None
                phone_time_zones = []
                
                for pn in getattr(lead, 'phone_numbers', []):
                    if pn.time_zone:
                        phone_time_zones.append(pn.time_zone.strip().lower())
                
                # Use the most common time zone, or first available
                if phone_time_zones:
                    from collections import Counter
                    time_zone_counter = Counter(phone_time_zones)
                    time_zone = time_zone_counter.most_common(1)[0][0]
                
                # If we have a valid time zone, use it, otherwise default to 'est'
                if time_zone and time_zone.lower() in time_zones:
                    leads_by_zone[time_zone.lower()].append(lead)
                else:
                    leads_by_zone['est'].append(lead)  # Default to EST if no time zone found

            # Calculate the total number of leads and determine the number of SalesShows needed
            total_leads = sum(len(leads) for leads in leads_by_zone.values())

            if total_leads <= 20:
                sales_shows_count = 1
            elif 20 < total_leads <= 50:
                sales_shows_count = 2
            elif 50 < total_leads <= 100:
                sales_shows_count = 4
            elif 100 < total_leads <= 200:
                sales_shows_count = 8
            elif 200 < total_leads <= 400:
                sales_shows_count = 16
            elif 400 < total_leads <= 800:
                sales_shows_count = 32
            elif 800 < total_leads <= 1600:
                sales_shows_count = 64
            else:
                sales_shows_count = total_leads // 100  # Continuing the pattern (dividing by 100 for very large groups)

            # Create empty lists for each SalesShow to hold leads
            sales_show_leads = [[] for _ in range(sales_shows_count)]

            # Distribute leads from each time zone across the SalesShow objects evenly
            for tz, leads in leads_by_zone.items():
                zone_lead_count = len(leads)
                split_size = zone_lead_count // sales_shows_count

                for i in range(sales_shows_count):
                    start_index = i * split_size
                    end_index = start_index + split_size
                    sales_show_leads[i].extend(leads[start_index:end_index])

                # Handle leftover leads (if any) from the current time zone
                leftover_leads = leads[sales_shows_count * split_size:]
                for i, lead in enumerate(leftover_leads):
                    sales_show_leads[i % sales_shows_count].append(lead)

            # Create SalesShows and assign the leads to them
            for idx, leads_chunk in enumerate(sales_show_leads, start=1):
                sales_show_name = f"{ready_show.sheet.name} ({idx})"  # Append number to SalesShow name
                sales_show = SalesShow.objects.create(
                    name=sales_show_name,
                    sheet=ready_show.sheet,
                    is_done=False,
                    label=ready_show.label
                )
                sales_show.leads.add(*leads_chunk)
                sales_show.save()

        # Handle referrals
        for lead in leads_to_referral:
            Referral.objects.create(lead=lead, sheet=ready_show.sheet)
            
        # Success Notification
        notification = Notification.objects.create(
            sender=user,
            receiver=user,
            message=f'Ready show {ready_show.name} cut successfully',
            notification_type=0, # Info
            read=False
        )
        send_websocket_message(user.id, notification.id, notification.message, notification.read, NOTIFICATIONS_STATES['INFO'])

    except Exception as e:
        print(f"Error cutting ready show: {e}")
        if user:
            notification = Notification.objects.create(
                sender=user,
                receiver=user,
                message=f'Error cutting ready show {ready_show_id}: {str(e)}',
                notification_type=2, # Error
                read=False
            )
            send_websocket_message(user.id, notification.id, notification.message, notification.read, NOTIFICATIONS_STATES['ERROR'])
