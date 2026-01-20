from celery import shared_task
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import models
from main.models import (
    Sheet, ReadyShow, SalesShow, LeadTerminationHistory, Referral,
    FilterWords, LeadEmails, LeadPhoneNumbers, LeadContactNames, LeadsColors,
    Notification, User
)
from main.utils import send_websocket_message, NOTIFICATIONS_STATES
import openpyxl
import os

@shared_task
def cut_sheet_into_ready_show_task(sheet_id, user_id):
    user = None
    try:
        user = User.objects.get(id=user_id)
        # Get the sheet and mark it as done
        sheet = Sheet.objects.get(id=sheet_id)
        sheet.is_done = True
        sheet.done_date = timezone.now()
        sheet.save()

        # Define country sets
        uk_countries = {'scotland', 'wales', 'england', 'ireland', 'uk'}

        europe_countries = {
            'poland', 'france', 'lithuania', 'sweden', 'spain', 'russia', 'austria',
            'czechia', 'belarus', 'latvia', 'malta', 'greece', 'andorra', 'moldova',
            'turkiye', 'georgia', 'germany', 'bulgaria', 'norway', 'romania',
            'estonia', 'san marino', 'slovenia', 'switzerland', 'montenegro', 'croatia',
            'bosnia & herzegovina', 'isle of man', 'kosovo', 'luxembourg', 'hungary',
            'netherlands', 'italy', 'portugal', 'denmark', 'finland', 'ukraine',
            'north macedonia', 'lichtenstein', 'slovakia', 'belgium', 'monaco',
            'albania', 'cyprus', 'kazakhstan'
        }

        asia_countries = {
            'india', 'indonesia', 'pakistan', 'bangladesh', 'japan', 'philippines',
            'vietnam', 'iran', 'thailand', 'south korea', 'malaysia', 'saudi arabia',
            'nepal', 'sri lanka', 'cambodia', 'jordan', 'united arab emirates',
            'tajikistan', 'azerbaijan', 'israel', 'laos', 'turkmenistan', 'kyrgyzstan',
            'singapore', 'oman', 'kuwait', 'mongolia', 'qatar', 'armenia', 'bahrain',
            'maldives', 'brunei', 'hong kong', 'china'
        }

        # Initialize containers
        leads_to_referral = []
        na_leads = {'cen': [], 'est': [], 'pac': []}
        region_leads = {'UK': [], 'Europe': [], 'Asia': []}
        red_blue_na_leads = {'cen': [], 'est': [], 'pac': []}
        red_blue_region_leads = {'UK': [], 'Europe': [], 'Asia': []}

        def get_shows_count(total_leads):
            if total_leads <= 20:
                return 1
            elif total_leads <= 50:
                return 2
            elif total_leads <= 100:
                return 4
            elif total_leads <= 200:
                return 8
            else:
                return total_leads // 10

        # Process all leads
        all_leads = sheet.leads.all()
        
        # Prefetch phone numbers with time zones for all leads
        from django.db.models import Prefetch
        phone_numbers_prefetch = Prefetch(
            'leadphonenumbers_set',
            queryset=LeadPhoneNumbers.objects.filter(sheet=sheet),
            to_attr='phone_numbers'
        )
        all_leads = all_leads.prefetch_related(phone_numbers_prefetch)

        for lead in all_leads:
            # Handle referrals
            if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name__in=['show', 'CD']).exists():
                if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name='CD').exists():
                    leads_to_referral.append(lead)
                continue

            # Determine lead's time zone based on phone numbers
            time_zone = None
            region = None
            
            # Get time zones from all phone numbers for this lead
            phone_time_zones = []
            for pn in getattr(lead, 'phone_numbers', []):
                if pn.time_zone:
                    phone_time_zones.append(pn.time_zone.strip().lower())
            
            # Use the most common time zone, or first available
            if phone_time_zones:
                from collections import Counter
                time_zone_counter = Counter(phone_time_zones)
                time_zone = time_zone_counter.most_common(1)[0][0]
            else:
                # If no phone numbers with time zones, check if it's a regional lead
                pass

            # If we have a valid NA time zone, use it
            if time_zone and time_zone.lower() in ['cen', 'est', 'pac']:
                time_zone_lower = time_zone.lower()
            else:
                # For regional leads, determine region based on country/time_zone data
                time_zone_lower = ''
                # Check if any phone number time_zone indicates a region
                for pn in getattr(lead, 'phone_numbers', []):
                    if pn.time_zone:
                        tz_lower = pn.time_zone.strip().lower()
                        if tz_lower in uk_countries:
                            region = 'UK'
                            break
                        elif tz_lower in europe_countries:
                            region = 'Europe'
                            break
                        elif tz_lower in asia_countries:
                            region = 'Asia'
                            break

            # Sort leads based on color and region/time_zone
            if sheet.is_x and LeadsColors.objects.filter(lead=lead, sheet=sheet, color__in=['red', 'blue']).exists():
                if time_zone_lower in ['cen', 'est', 'pac']:
                    red_blue_na_leads[time_zone_lower].append(lead)
                elif region:
                    red_blue_region_leads[region].append(lead)
                else:
                    # If no time zone or region found, put in EST as default
                    red_blue_na_leads['est'].append(lead)
            else:
                if time_zone_lower in ['cen', 'est', 'pac']:
                    na_leads[time_zone_lower].append(lead)
                elif region:
                    region_leads[region].append(lead)
                else:
                    # If no time zone or region found, put in EST as default
                    na_leads['est'].append(lead)

        def distribute_na_leads_evenly(leads_dict, num_shows):
            shows_leads = [[] for _ in range(num_shows)]
            
            for zone in ['cen', 'est', 'pac']:
                leads = leads_dict[zone]
                zone_lead_count = len(leads)
                split_size = zone_lead_count // num_shows if num_shows > 0 else 0
                
                for i in range(num_shows):
                    start_idx = i * split_size
                    end_idx = start_idx + split_size
                    shows_leads[i].extend(leads[start_idx:end_idx])
                
                # Handle leftover leads
                leftover_leads = leads[num_shows * split_size:]
                for i, lead in enumerate(leftover_leads):
                    shows_leads[i % num_shows].append(lead)
            
            return shows_leads

        # Handle red/blue leads first if sheet is_x
        if sheet.is_x:
            # Process NA red/blue leads
            total_na_red_blue = sum(len(leads) for leads in red_blue_na_leads.values())
            if total_na_red_blue > 0:
                sales_shows_count = get_shows_count(total_na_red_blue)
                na_sales_show_leads = distribute_na_leads_evenly(red_blue_na_leads, sales_shows_count)
                
                for idx, leads_chunk in enumerate(na_sales_show_leads, start=1):
                    sales_show = SalesShow.objects.create(
                        name=f"{sheet.name} X ({idx})",
                        sheet=sheet,
                        is_done=False,
                        is_x=True,
                        label="EHUB"  # Default label for NA sales shows
                    )
                    sales_show.leads.add(*leads_chunk)
                    sales_show.save()

            # Process regional red/blue leads
            for region, leads in red_blue_region_leads.items():
                if leads:
                    region_count = len(leads)
                    shows_count = get_shows_count(region_count)
                    
                    # Split leads into chunks
                    chunk_size = len(leads) // shows_count
                    for i in range(shows_count):
                        start_idx = i * chunk_size
                        end_idx = start_idx + chunk_size if i < shows_count - 1 else len(leads)
                        
                        sales_show = SalesShow.objects.create(
                            name=f"{sheet.name} {region} ({i+1})",
                            sheet=sheet,
                            is_done=False,
                            is_x=True,
                            label=region  # Regional label for regional sales shows
                        )
                        sales_show.leads.add(*leads[start_idx:end_idx])
                        sales_show.save()

        # Create ReadyShows for remaining leads (both for X and non-X sheets)
        # First, create 3 ReadyShows for NA leads
        labels = ['EHUB', 'EHUB2', 'EP']
        na_ready_shows = [
            ReadyShow.objects.create(
                sheet=sheet,
                label=label,
                name=f"{sheet.name} - {label}",
            ) for label in labels
        ]
        
        # Distribute NA leads evenly across the 3 shows
        na_ready_show_leads = distribute_na_leads_evenly(na_leads, 3)
        for show, leads in zip(na_ready_shows, na_ready_show_leads):
            show.leads.add(*leads)
            show.save()

        # Create one ReadyShow for each region
        for region, leads in region_leads.items():
            if leads:
                ready_show = ReadyShow.objects.create(
                    sheet=sheet,
                    label=region,
                    name=f"{sheet.name} - {region}",
                )
                ready_show.leads.add(*leads)
                ready_show.save()

        # Handle referrals
        for lead in leads_to_referral:
            Referral.objects.create(lead=lead, sheet=sheet)

        # Handle emails
        workbook = openpyxl.Workbook()
        sheet_ws = workbook.active
        sheet_ws.title = "Leads"
        sheet_ws.append(["Company Name", "Email"])
        
        if sheet.is_x:
            # For X sheets, only include red/blue leads
            email_leads = [
                lead for lead in all_leads
                if LeadsColors.objects.filter(lead=lead, sheet=sheet, color__in=['red', 'blue']).exists()
            ]
        else:
            # For non-X sheets, include all leads
            email_leads = all_leads

        for lead in email_leads:
            if LeadTerminationHistory.objects.filter(lead=lead, termination_code__name__in=['show', 'CD']).exists():
                continue
            if FilterWords.objects.filter(word=lead.name, filter_types__name='email').exists():
                continue

            lead_email_obj = LeadEmails.objects.filter(lead=lead, sheet=sheet).first()
            if lead_email_obj:
                lead_email = lead_email_obj.value
                sheet_ws.append([lead.name, lead_email])

        # Save the Excel workbook bytes directly in the database instead of external storage
        from io import BytesIO

        excel_file = BytesIO()
        workbook.save(excel_file)
        sheet.generated_mail_content = excel_file.getvalue()
        sheet.save(update_fields=["generated_mail_content"])

        # Success Notification
        notification = Notification.objects.create(
            sender=user, # System or user himself
            receiver=user,
            message=f'Sheet {sheet.name} cut successfully',
            notification_type=0, # Info
            read=False
        )
        send_websocket_message(user.id, notification.id, notification.message, notification.read, NOTIFICATIONS_STATES['INFO'])
    
    except Exception as e:
        # Failure Notification
        print(f"Error cutting sheet: {e}")
        if user:
            notification = Notification.objects.create(
                sender=user,
                receiver=user,
                message=f'Error cutting sheet {sheet_id}: {str(e)}',
                notification_type=2, # Error/Warning
                read=False
            )
            send_websocket_message(user.id, notification.id, notification.message, notification.read, NOTIFICATIONS_STATES['ERROR'])
