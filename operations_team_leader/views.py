from main.models import Lead, LeadContactNames, LeadEmails, LeadPhoneNumbers, Notification, Sheet, Acceptance, LeadsAverage, ReadyShow, Log, FilterWords, FilterType, LeadsColors
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import user_passes_test
from main.custom_decorators import is_in_group
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import pandas as pd
import logging, os
from django.core.exceptions import ObjectDoesNotExist
from IBH import settings
from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect
from urllib.parse import unquote
from django.db.models import OuterRef, Subquery
from main.utils import clean_company_name, filter_companies, get_string_value, has_valid_contact, is_valid_phone_number, send_websocket_message, NOTIFICATIONS_STATES
from collections import defaultdict
from django.db import transaction
from django.contrib import messages


logger = logging.getLogger('custom')

# Variable used as a shortcut for opsTL 
TL = 'operations_team_leader'

@user_passes_test(lambda user: is_in_group(user, TL))
def index(request):
    query = request.GET.get('q')
    
    # Get the most recent phone number, email, and contact name
    recent_phone_number = LeadPhoneNumbers.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]
    recent_time_zone = LeadPhoneNumbers.objects.filter(lead=OuterRef('pk')).order_by('-id').values('time_zone')[:1]
    recent_email = LeadEmails.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]
    recent_contact_name = LeadContactNames.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]

    if query:
        leads = Lead.objects.filter(name__icontains=query).order_by("-id")
    else:
        leads = Lead.objects.none()
    
    # Annotate leads with recent contact information
    leads = leads.annotate(
        recent_phone_number=Subquery(recent_phone_number),
        recent_time_zone=Subquery(recent_time_zone),
        recent_email=Subquery(recent_email),
        recent_contact_name=Subquery(recent_contact_name)
    )
    
    page = request.GET.get('page', '')
    paginator = Paginator(leads[:10 * 30], 30)  

    try:
        leads_page = paginator.page(page)
    except PageNotAnInteger:
        leads_page = paginator.page(1)
    except EmptyPage:
        leads_page = paginator.page(paginator.num_pages)

    return render(request, 'operations_team_leader/index.html', {
        'leads': leads_page,
        'query': query
    })


@user_passes_test(lambda user: is_in_group(user, TL))
def notifications(request):
    user = request.user
    notifications_for_user = Notification.objects.filter(
        receiver=user).order_by('-created_at')

    # Implement pagination
    page = request.GET.get('page', '')
    # Show 10 notifications per page
    paginator = Paginator(notifications_for_user, 50)

    try:
        notifications_page = paginator.page(page)
    except PageNotAnInteger:
        notifications_page = paginator.page(1)
    except EmptyPage:
        notifications_page = paginator.page(paginator.num_pages)

    return render(request, TL + '/notifications.html', {
        'notifications': notifications_page
    })


@user_passes_test(lambda user: is_in_group(user, TL))
def notification_detail(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    sheets = notification.sheets.all()
    
    if not notification.read:
        notification.read = True
        notification.save()

    return render(request, TL + '/notification_detail.html',{
        'notification': notification,
        'sheets': sheets
    })
    

@user_passes_test(lambda user: is_in_group(user, TL))
def accept_upload_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    sheets = notification.sheets.all()

    template_name = "operations_team_leader/notifications.html"  # Adjust as necessary
    new_leads_count = 0
    lead_cache = {}

    if request.method == 'POST':
        for sheet in sheets:
            file_path = os.path.join(settings.MEDIA_ROOT, 'upload', str(sheet.name))
            file_extension = sheet.name.split('.')[-1]

            if file_extension == 'xlsx':
                data = pd.read_excel(file_path, engine='openpyxl')
            elif file_extension == 'xls':
                data = pd.read_excel(file_path)
            elif file_extension == 'csv':
                data = pd.read_csv(file_path)
            else:
                messages.error(request, "Unsupported file format.")
                return render(request, template_name, {"notification": notification})

            if data.empty:
                messages.error(request, "The uploaded file is empty.")
                continue  # Skip to the next sheet

            # Clean & Filter company names
            if 'Company Name' in data.columns:
                data['Company Name'] = data['Company Name'].map(clean_company_name)
                data = data[data['Company Name'].apply(filter_companies)]

            for _, row in data.iterrows():
                if not has_valid_contact(row):
                    continue
                
                company_name = row.get('Company Name', '')

                # Create or get the lead
                lead, created = Lead.objects.get_or_create(name=company_name)

                if created:
                    new_leads_count += 1

                # Update lead attributes
                lead.time_zone = get_string_value(row, 'Time Zone')
                lead.save()

                # Handle phone numbers
                phone_number = get_string_value(row, 'Phone Number')
                direct_cell_number = get_string_value(row, 'Direct / Cell Number') if 'Direct / Cell Number' in data.columns else None
                phone_numbers = ','.join(filter(None, [phone_number, direct_cell_number]))

                if phone_numbers:
                    for number in phone_numbers.split(','):
                        number = number.strip()
                        if number and is_valid_phone_number(number):
                            LeadPhoneNumbers.objects.get_or_create(lead=lead, sheet=sheet, value=number)

                # Handle email
                email = get_string_value(row, 'Email')
                if email:
                    LeadEmails.objects.get_or_create(lead=lead, sheet=sheet, value=email)

                # Handle contact name
                contact_name = get_string_value(row, 'DM Name')
                if contact_name:
                    LeadContactNames.objects.get_or_create(lead=lead, sheet=sheet, value=contact_name)

                # Handle color if 'Color' column exists
                if 'Color' in data.columns:
                    color = get_string_value(row, 'Color')
                    if color and color.lower() in ['white', 'green', 'blue', 'red']:
                        LeadsColors.objects.create(lead=lead, sheet=sheet, color=color.lower())

                # Link the lead to the sheet
                sheet.leads.add(lead)

            # Mark the sheet as approved
            sheet.is_approved = True
            sheet.save()

        # Update notification
        notification.is_accepted = True
        notification.save()

        # Create a success message
        if new_leads_count > 0:
            LeadsAverage.objects.create(user=request.user, sheet=sheet, count=new_leads_count)

        messages.success(request, f"Successfully accepted upload with {new_leads_count} new leads.")

        # Add a log entry
        logger.info(f"{request.user.username} accepted uploads with {new_leads_count} new leads.")
        Log.objects.create(message=f"{request.user.username} accepted uploads with {new_leads_count} new leads.")

        return render(request, template_name, {"notification": notification})

    messages.error(request, "Invalid request method.")
    return render(request, template_name, {"notification": notification})


@user_passes_test(lambda user: is_in_group(user, TL))
def decline_upload_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    sheets = notification.sheets.all()
    
    # Loop over all sheets
    for sheet in sheets:
        # Get sheet name
        sheet_name = sheet.name
        
        # Delete sheet file from uploads folder
        file_path = os.path.join(settings.MEDIA_ROOT, 'upload', str(sheet_name))
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Create an acceptance record
        Acceptance.objects.create(sheet=sheet, team_leader=request.user, acceptance_type=0)
        
        # Delete the sheet from the database
        sheet.delete()

    # Update notification as declined
    notification.is_accepted = True
    notification.save()
        
    lead_user = notification.sender
    
    # Create a new notification for the Lead user
    lead_notification = Notification.objects.create(
        sender=request.user,
        receiver=lead_user,
        message=f'Your import request has been declined by {request.user.username} for sheet: {sheet.name}',
        notification_type=2,  # Decline request notification type
        read=False
    )
    
    lead_notification.save()
        
    # Send a websocket message to the Lead user
    send_websocket_message(lead_user.id, lead_notification.id, lead_notification.message,
                           lead_notification.read,  NOTIFICATIONS_STATES['ERROR'])

    # Redirect to a confirmation page or back to the notifications list
    return HttpResponseRedirect(reverse('operations_team_leader:notifications'))


@user_passes_test(lambda user: is_in_group(user, TL))
def view_sheet(request, notification_id, sheet_id):
    notification = get_object_or_404(Notification, id=notification_id)
    sheet = get_object_or_404(Sheet, id=sheet_id) 
    
    sheet_name = sheet.name
    
    # Determine the correct file path based on the notification type
    if notification.notification_type == 0:  # Import Request
        file_path = os.path.join(settings.MEDIA_ROOT, 'upload', str(sheet_name))
    elif notification.notification_type == 3:  # Autofill Request
        file_path = os.path.join(settings.MEDIA_ROOT, 'auto_fill', str(sheet_name))
    else:
        # Handle other cases if needed or raise an error
        raise ValueError("Unsupported notification type for this view.")
    
    # Read leads data from the Excel sheet named sheet_name
    data = pd.DataFrame()
    file_extension = sheet_name.split('.')[-1]
    if file_extension == 'xlsx':
        data = pd.read_excel(file_path, engine='openpyxl')
    elif file_extension == 'xls':
        data = pd.read_excel(file_path)
    elif file_extension == 'csv':
        data = pd.read_csv(file_path)
    
    # Clean & Filter company names
    if 'Company Name' in data.columns:
        # data['Company Name'] = data['Company Name'].map(clean_company_name)
        data = data[data['Company Name'].apply(filter_companies)]

    # Extract the relevant data to be displayed in the template
    leads = []
    if not data.empty:
        for _, row in data.iterrows():
            company_name = row['Company Name']

            time_zone = row['Time Zone']
            
            # Extract and clean phone numbers
            phone_number = get_string_value(row, 'Phone Number')
            direct_cell_number = get_string_value(row, 'Direct / Cell Number')
            
            # Combine phone numbers into a single string, ignoring empty entries
            phone_numbers = ','.join(filter(None, [phone_number, direct_cell_number]))

            # Split the phone numbers by a separator and iterate over each
            phone_numbers_list = [phone_number.strip() for phone_number in phone_numbers.split(',') if phone_number.strip()]
            
            # Extract email and contact name
            email = get_string_value(row, 'Email')
            contact_name = get_string_value(row, 'DM Name')
            
            # Append the extracted information to leads list
            leads.append({
                'company_name': company_name,
                'time_zone': time_zone,
                'phone_numbers': phone_numbers_list,
                'email': email,
                'contact_name': contact_name,
            })

    return render(request, TL + '/view_sheet.html', {'sheet': sheet, 'leads': leads, 'notification': notification})


@require_POST
@user_passes_test(lambda user: is_in_group(user, TL))
def delete_excel_lead(request, notification_id, sheet_id, company_name):
    notification = get_object_or_404(Notification, id=notification_id)
    sheet = get_object_or_404(Sheet, id=sheet_id)
    company_name = unquote(company_name)  # Decode the company name

    # Determine the correct file path based on the notification type
    if notification.notification_type == 0:  # Import Request
        file_path = os.path.join(settings.MEDIA_ROOT, 'upload', str(sheet.name))
    elif notification.notification_type == 3:  # Autofill Request
        file_path = os.path.join(settings.MEDIA_ROOT, 'auto_fill', str(sheet.name))
    
    # Load the sheet data
    file_extension = sheet.name.split('.')[-1]
    if file_extension == 'xlsx':
        df = pd.read_excel(file_path, engine='openpyxl')
    elif file_extension == 'xls':
        df = pd.read_excel(file_path)
    elif file_extension == 'csv':
        df = pd.read_csv(file_path)
    
    # Delete the lead data
    df = df[df['Company Name'] != company_name]
    
    # Save the updated data back to the file
    if file_extension == 'xlsx':
        df.to_excel(file_path, index=False, engine='openpyxl')
    elif file_extension == 'xls':
        df.to_excel(file_path, index=False)
    elif file_extension == 'csv':
        df.to_csv(file_path, index=False)
        
    # Redirect to the generated URL
    return HttpResponseRedirect(reverse('operations_team_leader:view-sheet', args=[notification_id, sheet_id]))


@user_passes_test(lambda user: is_in_group(user, TL))
def edit_excel_lead(request, notification_id, sheet_id, company_name):
    notification = get_object_or_404(Notification, id=notification_id)
    sheet = get_object_or_404(Sheet, id=sheet_id)
    company_name = unquote(company_name)

    # Determine the correct file path based on the notification type
    if notification.notification_type == 0:  # Import Request
        file_path = os.path.join(settings.MEDIA_ROOT, 'upload', str(sheet.name))
    elif notification.notification_type == 3:  # Autofill Request
        file_path = os.path.join(settings.MEDIA_ROOT, 'auto_fill', str(sheet.name))
    
    # Load the sheet data
    file_extension = sheet.name.split('.')[-1]
    if file_extension == 'xlsx':
        df = pd.read_excel(file_path, engine='openpyxl')
    elif file_extension == 'xls':
        df = pd.read_excel(file_path)
    elif file_extension == 'csv':
        df = pd.read_csv(file_path)
    
    # Get the lead data
    lead_data = df[df['Company Name'] == company_name]
    
    if lead_data.empty:
        return redirect('operations_team_leader:sheet-detail', notification_id=notification_id, sheet_id=sheet_id)

    lead_data = lead_data.iloc[0]  # Get the first match
    
    if request.method == 'POST':
        # Update the lead data with the submitted form data
        df.loc[df['Company Name'] == company_name, 'Phone Number'] = request.POST['phone_number']
        df.loc[df['Company Name'] == company_name, 'Direct / Cell Number'] = request.POST['direct_cell_number']
        df.loc[df['Company Name'] == company_name, 'Email'] = request.POST['email']
        df.loc[df['Company Name'] == company_name, 'DM Name'] = request.POST['contact_name']
        
        # Save the updated data back to the file
        if file_extension == 'xlsx':
            df.to_excel(file_path, index=False, engine='openpyxl')
        elif file_extension == 'xls':
            df.to_excel(file_path, index=False)
        elif file_extension == 'csv':
            df.to_csv(file_path, index=False)
        
        # Redirect to the generated URL
        return HttpResponseRedirect(reverse('operations_team_leader:view-sheet', args=[notification_id, sheet_id]))

    context = {
        'notification': notification,
        'sheet': sheet,
        'company_name': lead_data['Company Name'],
        'phone_number': lead_data.get('Phone Number', ''),
        'direct_cell_number': lead_data.get('Direct / Cell Number', ''),
        'email': lead_data.get('Email', ''),
        'contact_name': lead_data.get('DM Name', ''),
    }
    return render(request, TL + '/edit_excel_lead.html', context)


@user_passes_test(lambda user: is_in_group(user, TL))
def accept_auto_fill_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    sheet = notification.sheets.first()
    receiver_user = sheet.user
    sender_user = request.user 

    new_notification = Notification.objects.create(
        sender=sender_user,
        receiver=receiver_user,
        message="Your auto fill request has been accepted",
        notification_type=4,
    )

    new_notification.sheets.set([sheet])
    new_notification.is_accepted=True
    new_notification.save()

    notification.is_accepted=True
    notification.save()

    send_websocket_message(receiver_user.id, new_notification.id,
                           new_notification.message, new_notification.read,  NOTIFICATIONS_STATES['SUCCESS'])

    return HttpResponseRedirect(reverse("operations_team_leader:notifications"))

