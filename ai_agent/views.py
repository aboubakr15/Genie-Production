
from django.shortcuts import render
from .forms import CompanyListForm
from main.models import Lead, LeadEmails, LeadPhoneNumbers, LeadContactNames
from .models import GlobalOrganization, GlobalPhoneNumbers, GlobalEmails, GlobalContactNames
import requests
from django.contrib.auth.decorators import user_passes_test
from main.custom_decorators import is_in_group


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
    global_data = search_global_database(company_name)
    if global_data:
        # Copy to local if desired
        # Lead.objects.get_or_create(name=company_name)
        return {'source': 'global', 'data': global_data}

    # AI Agent
    AI_data = ai_search(company_name)
    if AI_data:
        return {'source': 'AI', 'data': AI_data}
    
    # Apollo
    apollo_data = fetch_and_save_apollo(company_name)
    if apollo_data:
        return {'source': 'apollo', 'data': apollo_data}

    return {'source': 'not_found', 'data': None}




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


def ai_search(company_name, sheet):
    """
    Search local database for the company and return phones, emails, contacts if found.
    Returns dict like {'phones': [...], 'emails': [...], 'contacts': [...]} or None if not found.
    """
    # Dummy DeepSeek API endpoint and key (replace with real values)
    DEEPSEEK_API_URL = 'https://api.deepseek.com/company-info'
    DEEPSEEK_API_KEY = 'YOUR_DEEPSEEK_API_KEY'

    # def get_deepseek_data(company_names):
        # This function should call the DeepSeek API for company names not found in the DB
        # return results

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




