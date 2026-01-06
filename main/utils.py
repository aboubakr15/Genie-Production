import re, math
from main.models import LeadContactNames, LeadEmails, LeadPhoneNumbers, FilterType, FilterWords
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


NOTIFICATIONS_STATES = {
    'SUCCESS': 'SUCCESS',
    'INFO': 'INFO',
    'WARNING': 'WARNING',
    'ERROR': 'ERROR'
}

def send_websocket_message(user_id, notification_id, message, read, notification_state):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user_id}',
        {
            'type': 'send_notification',
            'message': message,
            'id': notification_id,
            'read': read,
            'state': notification_state
        }
    )


# Clean company names before importing them to the database.
def clean_company_name(name):
    # Check if the name is a float and handle NaN values
    if isinstance(name, float):
        if math.isnan(name):
            return ''  # Return an empty string for NaN values
        else:
            name = str(name)  # Convert other floats to strings

    # Convert name to string if it's not already
    if not isinstance(name, str):
        name = str(name)

    # List of patterns like (inc, LLC, etc...) to filter out
    patterns = [
        r'\s*,?\s*inc\.?\s*(?:\(.+?\))?\s*$',
        r'\s*,?\s*co\.?\s*(?:\(.+?\))?\s*$',
        r'\s*,?\s*ltd\.?\s*(?:\(.+?\))?\s*$',
        r'\s*,?\s*llc\s*(?:\(.+?\))?\s*$',
        r'\s*,?\s*llp\s*(?:\(.+?\))?\s*$',
        r'\s*,?\s*lp\s*(?:\(.+?\))?\s*$',
        r'\s*,?\s*plc\s*(?:\(.+?\))?\s*$',
    ]

    combined_pattern = re.compile('|'.join(patterns), re.IGNORECASE)

    cleaned_name = combined_pattern.sub('', name).strip()

    if cleaned_name.endswith(".") or cleaned_name.endswith(','):
        cleaned_name = cleaned_name[:-1]

    return cleaned_name


# Delete filtered organizations from the excel file.
def filter_companies(name):
    # Get the filter type for phone numbers
    phone_filter_type = FilterType.objects.get(name='phone_number')

    # Query the filter words for the 'phone_number' filter type
    filter_words_qs = FilterWords.objects.filter(filter_types=phone_filter_type)

    # Extract the words from the query set
    filter_words = {fw.word.lower() for fw in filter_words_qs}  # Use a set for faster lookups

    # Split the name into words and convert to lowercase
    name_words = set(name.lower().split())

    # Check if any filtered word is exactly present in the name words
    return not any(word in name_words for word in filter_words)


def is_valid_phone_number(phone_number):
    # Define a regex pattern for valid phone numbers
    phone_pattern = re.compile(r'^[+\d\s\(\)-]+$')
    return bool(phone_pattern.match(phone_number)) and re.search(r'\d', phone_number)


def has_valid_contact(row):
    phone_number = get_string_value(row, 'Phone Number')
    direct_cell_number = get_string_value(row, 'Direct / Cell Number')
    email = get_string_value(row, 'Email')
    
    # Validate phone numbers and email
    valid_phone = any(is_valid_phone_number(phone_number) for phone_number in [phone_number, direct_cell_number] if phone_number)
    valid_email = bool(email)  # Assuming any non-empty string is a valid email
    
    return valid_phone or valid_email


def get_sheet_name(name: str) -> str:
    # Regular expression to match the sheet name
    match = re.match(r'^([a-zA-Z\s]+)\s\d{4}', name)
    if match:
        # print(get_sheet_name("test name 2024 - test - 4551"))  # Output: "test name"
        # print(get_sheet_name("example name 2023 - example - 1234")) # Output: "example name"
        return match.group(1).strip()
    return ""


def get_lead_related_data(lead):
    # Returns the latest contact data 
    phone_number = LeadPhoneNumbers.objects.filter(lead=lead).order_by('id').values_list('value', flat=True).last()
    time_zone = LeadPhoneNumbers.objects.filter(lead=lead).order_by('id').values_list('time_zone', flat=True).last()
    email = LeadEmails.objects.filter(lead=lead).order_by('id').values_list('value', flat=True).last()
    contact_name = LeadContactNames.objects.filter(lead=lead).order_by('id').values_list('value', flat=True).last()

    return (phone_number, time_zone, email, contact_name)


def get_string_value(row, key):
    """Safely get a string value from a dictionary, handling None and NaN."""
    value = row.get(key, '')

    # Convert to string if it's not already a string and handle NaN
    if isinstance(value, float) and math.isnan(value):
        return ''
    return str(value).strip()
