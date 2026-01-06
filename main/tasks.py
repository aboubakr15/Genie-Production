from celery import shared_task
import pandas as pd
from .utils import has_valid_contact, is_valid_phone_number, clean_company_name, filter_companies, get_string_value
from .models import Lead, Sheet, LeadContactNames, LeadEmails, LeadPhoneNumbers, LeadsAverage, User, LeadsColors
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime, timedelta
import pytz
import random
import string

def generate_random_string(length=5):
    """Generate a random string of fixed length."""
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for i in range(length))

@shared_task
def process_sheet_task(file_path, original_filename, user_id):
    """
    Celery task to process an uploaded sheet in the background.
    """
    try:
        user = User.objects.get(id=user_id)
        
        if original_filename.endswith('.xlsx'):
            data = pd.read_excel(file_path, engine='openpyxl', header=None)
        elif original_filename.endswith('.xls'):
            data = pd.read_excel(file_path, header=None)
        elif original_filename.endswith('.csv'):
            data = pd.read_csv(file_path, header=None)
        else:
            # In a real-world scenario, you'd want better error handling here
            print(f"Unsupported file format: {original_filename}")
            return

        if data.empty:
            print(f"Uploaded file is empty: {original_filename}")
            return

        offset = timedelta(hours=3)
        egypt_timezone = pytz.timezone('Africa/Cairo')
        current_time_with_offset = datetime.now(egypt_timezone)

        def ensure_str(value):
            return str(value) if pd.notna(value) else ''

        expected_headers = ['Company Name', 'Phone Number', 'Time Zone', 'Email', 'DM Name']
        extended_expected_headers = ['Company Name', 'Phone Number', 'Time Zone', 'Direct / Cell Number', 'Email', 'DM Name']
        first_row_as_str = data.iloc[0].apply(ensure_str) if not data.empty else pd.Series()
        has_header = all(header.lower() in [col.lower() for col in first_row_as_str if col] for header in expected_headers)
        has_extended_header = all(header.lower() in [col.lower() for col in first_row_as_str if col] for header in extended_expected_headers)

        if has_header or has_extended_header:
            data.columns = data.iloc[0].apply(ensure_str).tolist()
            data = data[1:]
            if has_extended_header:
                for i, header in enumerate(extended_expected_headers):
                    if i >= len(data.columns) or data.columns[i] == '' or data.columns[i].lower() not in [h.lower() for h in extended_expected_headers]:
                        data.columns[i] = header
            else:
                for i, header in enumerate(expected_headers):
                    if i >= len(data.columns) or data.columns[i] == '' or data.columns[i].lower() not in [h.lower() for h in expected_headers]:
                        data.columns[i] = header
        else:
            num_cols = data.shape[1]
            default_columns = ['Company Name', 'Phone Number', 'Time Zone', 'Direct / Cell Number', 'Email', 'DM Name']
            data.columns = default_columns[:num_cols] + [f"Column_{i}" for i in range(num_cols - len(default_columns))]

        if 'Company Name' in data.columns:
            data['Company Name'] = data['Company Name'].map(clean_company_name)
            data = data[data['Company Name'].apply(filter_companies)]

        random_suffix = generate_random_string(5)
        unique_sheet_name = f"{original_filename}_{random_suffix}"

        sheet, created = Sheet.objects.get_or_create(
            name=unique_sheet_name,
            defaults={'user': user, 'created_at': current_time_with_offset}
        )

        new_leads_count = 0

        for _, row in data.iterrows():
            if not has_valid_contact(row):
                continue

            company_name = row.get('Company Name', '')
            lead, created = Lead.objects.get_or_create(name=company_name)

            if created:
                new_leads_count += 1

            phone_number = get_string_value(row, 'Phone Number')
            time_zone = get_string_value(row, 'Time Zone')
            if time_zone:
                phone_time_zone = time_zone
                lead.save()

            direct_cell_number = get_string_value(row, 'Direct / Cell Number') if 'Direct / Cell Number' in data.columns else None
            phone_numbers = ','.join(filter(None, [phone_number, direct_cell_number]))

            if phone_numbers:
                for phone_number in phone_numbers.split(','):
                    phone_number = phone_number.strip()
                    if phone_number and is_valid_phone_number(phone_number):
                        try:
                            LeadPhoneNumbers.objects.get(lead=lead, sheet=sheet, value=phone_number)
                        except ObjectDoesNotExist:
                            LeadPhoneNumbers.objects.create(lead=lead, sheet=sheet, value=phone_number, time_zone=phone_time_zone)

            email = get_string_value(row, 'Email')
            if email:
                try:
                    LeadEmails.objects.get(lead=lead, sheet=sheet, value=email)
                except ObjectDoesNotExist:
                    LeadEmails.objects.create(lead=lead, sheet=sheet, value=email)

            contact_name = get_string_value(row, 'DM Name')
            if contact_name:
                try:
                    LeadContactNames.objects.get(lead=lead, sheet=sheet, value=contact_name)
                except ObjectDoesNotExist:
                    LeadContactNames.objects.create(lead=lead, sheet=sheet, value=contact_name)

            if 'Color' in data.columns:
                color = get_string_value(row, 'Color')
                if color and color.lower() in ['white', 'green', 'blue', 'red']:
                    LeadsColors.objects.create(lead=lead, sheet=sheet, color=color.lower())

            sheet.leads.add(lead)

        sheet.is_approved = True
        sheet.save()

        if new_leads_count > 0:
            LeadsAverage.objects.create(
                user=user,
                sheet=sheet,
                count=new_leads_count,
                created_at=current_time_with_offset
            )
        
        # Here you could add a notification for the user
        print(f"Sheet '{original_filename}' processed successfully for user {user.username}. {new_leads_count} new leads added.")

    except Exception as e:
        # Log the error
        print(f"Error processing sheet {original_filename}: {e}")
        # Optionally, notify the user of the failure
