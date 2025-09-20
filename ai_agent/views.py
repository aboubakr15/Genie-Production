
from django.shortcuts import render
from .forms import CompanyListForm
from main.models import Lead, LeadEmails, LeadPhoneNumbers, LeadContactNames
from .models import GlobalOrganization, GlobalPhoneNumbers, GlobalEmails, GlobalContactNames
import requests
from django.contrib.auth.decorators import user_passes_test
from main.custom_decorators import is_in_group
import json, time, re
from typing import Dict, Optional, List
from google import genai
from google.genai import types

@user_passes_test(lambda user: is_in_group(user, "ai_agent"))
def index(request):
    return render(request, 'ai_agent/index.html')

@user_passes_test(lambda user: is_in_group(user, "ai_agent"))
def search(request):
    return render(request, 'ai_agent/search.html')

@user_passes_test(lambda user: is_in_group(user, "ai_agent"))
def data_enrichment_view(request):

    if request.method == 'POST':
        form = CompanyListForm(request.POST)
        if form.is_valid():
            company_names = form.cleaned_data['company_names'].splitlines()

            results = []
            for name in company_names:
                enrichment = enrich_company(name)
                results.append({
                    'company': name,
                    'source': enrichment['source'],
                    'phones': enrichment['data']['phones'] if enrichment['data'] else [],
                    'emails': enrichment['data']['emails'] if enrichment['data'] else [],
                    'contacts': enrichment['data']['contacts'] if enrichment['data'] else [],
                })

            return render(request, 'ai_agent/enrich.html', {'form': form, 'results': results})
    else:
        form = CompanyListForm()

    return render(request, 'ai_agent/enrich.html', {'form': form})


def enrich_company(company_name):
    """
    Main function: Try local, then global, then Apollo.
    Returns {'source': 'local/global/apollo', 'data': {'phones': [...], ...}} or {'source': 'not_found', 'data': None}
    """
    company_name = company_name.strip()
    if not company_name:
        return {'source': 'not_found', 'data': None}

    # Global DB
    # global_data = search_global_database(company_name)
    # if global_data:
    #     # Copy to local if desired
    #     # Lead.objects.get_or_create(name=company_name)
    #     return {'source': 'global', 'data': global_data}

    # AI Agent
    AI_data = ai_search(company_name)
    if AI_data:
        return {'source': 'AI', 'data': AI_data}
    
    # Apollo
    # apollo_data = fetch_and_save_apollo(company_name)
    # if apollo_data:
    #     return {'source': 'apollo', 'data': apollo_data}

    return {'source': 'not_found', 'data': None}


def ai_search(company_name: str, sheet=None) -> Optional[Dict]:
    
    GEMINI_API_KEY = "AIzaSyBuNSlfHDLXEWfr1GUCsHWoqeLKibEyT0E"

    prompt = f"""You are a precise business intelligence agent tasked with retrieving verified company contact information.
USE THE GOOGLE SEARCH TOOL to search the internet for the specified company and return only verifiable data, following these rules:

### Instructions
1. First, search Google for "{company_name}" to find their official website and contact information
2. Visit the company's official website if found and extract contact details
3. Search for additional verified sources like LinkedIn company or Facebook pages, Crunchbase, or official business directories

### Rules
1. Return only data verified from credible, current sources (company website, LinkedIn, company's Facebook page, Crunchbase).
2. Never guess or infer data or return common formats of data searched, only return real data. Mark missing/unverifiable fields as NULL.
3. You are strictly prohibited from returning fake linkedin profiles, fake emails, fake phone numbers, or guessed domains.
4. If domain exists, Mandatory website check:
   "Extract ALL emails/phones from the website's:
    - Contact page
    - Footer or header (every page)
    - Customer service pages
    - Press/Media kits
    If no dedicated contact page exists, scan homepage metadata."
5. Make sure not to use websites or social media from similar company names.
6. Check Google search result sidebar for phone/website.
7. Prioritize US and direct phone numbers that does not start with (888) over toll free numbers but if none get the toll free.
8. Do not return unverifiable data — only verified.
9. Include the source for each value.
10. Each cell must carry one value only, do not return multiple values and things like (or/and).

### Data Structure
Return data in valid JSON format:
{{
"company_name": "{company_name}",
"domain": {{"value": "Primary domain name", "source": "data source"}},
"address": {{"value": "company's address", "source": "data source"}},
"phone": {{"value": "Primary phone", "source": "data source"}},
"email": {{"value": "General Email", "source": "data source"}},
"key_personnel": [
    {{
    "name": "Full name",
    "phone": "cell phone number",
    "title": "Job title",
    "email": "Direct email",
    "source": "data source"
    }}
]
}}

### Search Query: {company_name}"""

    # Setup Gemini client
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        return {"phones": None, "emails": None, "contacts": []}


    # Define the grounding tool for web search
    grounding_tool = types.Tool(
        google_search=types.GoogleSearch()
    )

    config = types.GenerateContentConfig(
        temperature=0.0,  # maximum factual determinism
        # max_output_tokens=800,
        tools=[grounding_tool],
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )

        # Add comprehensive response validation
        if not response:
            print(f"No response received for {company_name} ")

        content = response.text
        
        if not content:
            print(f"Empty response content for {company_name} ")
            
        print("======================================================================")            
        print(f"Response for {company_name}:")
        print("------------------------------------------------------")            
        print(content)
        print("======================================================================")

        try:
            data = json.loads(content)

            # Clean and validate data with better error handling
            phone_data = data.get('phone', {})
            email_data = data.get('email', {})
            
            validated_data = {
                'phones': phone_data.get('value') if isinstance(phone_data, dict) and phone_data.get('value') else None,
                'emails': email_data.get('value') if isinstance(email_data, dict) and email_data.get('value') and '@' in str(email_data.get('value')) else None,
                'contacts': [
                    contact for contact in data.get('key_personnel', [])
                    if isinstance(contact, dict) and contact.get('name')
                ]
            }

            return validated_data

        except json.JSONDecodeError as e:
            print(f"Invalid JSON response for {company_name} : {e}")
            print(f"Raw content: {content[:500]}...")  # Show first 500 chars for debugging

    except Exception as e:
        print(f"Gemini request failed for {company_name} : {e}")
        
        # Check for specific API errors
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            print("API quota/rate limit exceeded. Consider adding longer delays.")
            time.sleep(5)  # Longer delay for quota issues
        elif "authentication" in str(e).lower() or "api_key" in str(e).lower():
            print("API authentication failed. Check your API key.")
            return {"phones": None, "emails": None, "contacts": []}


    print(f"Failed to get data for {company_name}")
    return {"phones": None, "emails": None, "contacts": []}




{
# ############################################################## Apollo's Part ##############################################################
# # url = "https://api.apollo.io/api/v1/mixed_companies/search/?q_organization_name=ricoh"

# # headers = {
# #     "accept": "application/json",
# #     "Cache-Control": "no-cache",
# #     "Content-Type": "application/json",
# #     "x-api-key": "cEP6VNN56grd0VBig6fXiQ"
# # }

# # response = requests.post(url, headers=headers)

# # print(response.text)


# url = "https://api.apollo.io/api/v1/mixed_people/search"

# headers = {
#     "accept": "application/json",
#     "Cache-Control": "no-cache",
#     "Content-Type": "application/json",
#     "x-api-key": "cEP6VNN56grd0VBig6fXiQ"
# }

# response = requests.post(url, headers=headers)

# print(response.text)
}




def search_global_database(company_name):
    """
    Search global database for the company and return phones, emails, contacts if found.
    Returns dict like {'phones': [...], 'emails': [...], 'contacts': [...]} or None if not found.
    """
    global_org = GlobalOrganization.objects.using('railway').filter(name__iexact=company_name).first()
    if global_org:
        phones = list(GlobalPhoneNumbers.objects.using('railway').filter(organization=global_org).values('value', 'time_zone'))
        emails = list(GlobalEmails.objects.using('railway').filter(organization=global_org).values('value'))
        contacts = list(GlobalContactNames.objects.using('railway').filter(organization=global_org).values('value'))
        return {'phones': phones, 'emails': emails, 'contacts': contacts}
    return None

def call_apollo_api(company_name):
    """
    Call Apollo's API with the company name.
    Returns the response dict or None on error.
    """
    try:
        url = f"https://api.apollo.io/api/v1/mixed_companies/search?q_organization_name={company_name}&page=1&per_page=30"

        headers = {
            "accept": "application/json",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "x-api-key": "cEP6VNN56grd0VBig6fXiQ"
        }

        response = requests.post(url, headers=headers)
        return response.json()
    except Exception as e:
        print(f"Apollo API error: {e}")
        return None

def fetch_and_save_apollo(company_name, sheet):
    """
    Call Apollo API, save all organizations to global DB, save first to local DB.
    Returns dict {'phones': [...], 'emails': [...], 'contacts': [...]} from the first organization.
    """
    apollo_response = call_apollo_api(company_name)
    if not apollo_response:
        return None

    organizations = apollo_response.get('organizations', [])
    if not organizations:
        return None

    # Save all to global
    for org in organizations:
        defaults = {
            'apollo_id': org.get('id'),
            'website_url': org.get('website_url'),
            'angellist_url': org.get('angellist_url'),
            'linkedin_url': org.get('linkedin_url'),
            'twitter_url': org.get('twitter_url'),
            'facebook_url': org.get('facebook_url'),
            'alexa_ranking': org.get('alexa_ranking'),
            'linkedin_uid': org.get('linkedin_uid'),
            'founded_year': org.get('founded_year'),
            'logo_url': org.get('logo_url'),
            'crunchbase_url': org.get('crunchbase_url'),
            'primary_domain': org.get('primary_domain'),
            'sanitized_phone': org.get('sanitized_phone'),
            'owned_by_organization_id': org.get('owned_by_organization_id'),
        }
        global_org, _ = GlobalOrganization.objects.using('railway').get_or_create(name=org['name'], defaults=defaults)

        # Save phone
        primary_phone = org.get('primary_phone')
        if primary_phone:
            GlobalPhoneNumbers.objects.get_or_create(
                organization=global_org,
                value=primary_phone.get('number'),
                defaults={
                    'source': primary_phone.get('source'),
                    'sanitized_number': primary_phone.get('sanitized_number'),
                    'time_zone': None,  # Not in Apollo
                }
            )

        # Apollo doesn't provide emails/contacts in sample, so skip

    # Save first to local
    first_org = organizations[0]
    local_lead, _ = Lead.objects.get_or_create(name=first_org['name'])
    primary_phone = first_org.get('primary_phone')
    if primary_phone:
        LeadPhoneNumbers.objects.get_or_create(
            lead=local_lead,
            sheet=sheet,
            value=primary_phone.get('number'),
            defaults={'time_zone': None}
        )
    # No emails/contacts

    # Return data from first (now in local, but fetch to match format)
    return search_local_database(first_org['name'], sheet)

