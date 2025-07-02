
from django.shortcuts import render
from .forms import CompanyListForm
from main.models import Lead, LeadEmails, LeadPhoneNumbers, LeadContactNames
import requests

# Dummy DeepSeek API endpoint and key (replace with real values)
DEEPSEEK_API_URL = 'https://api.deepseek.com/company-info'
DEEPSEEK_API_KEY = 'YOUR_DEEPSEEK_API_KEY'

# def get_deepseek_data(company_names):
    # This function should call the DeepSeek API for company names not found in the DB
    # return results

def index(request):
    results = []
    not_found = []
    if request.method == 'POST':
        form = CompanyListForm(request.POST)
        if form.is_valid():
            company_list = form.cleaned_data['companies'].splitlines()
            company_list = [c.strip() for c in company_list if c.strip()]
            db_leads = Lead.objects.filter(name__in=company_list)
            db_lead_names = set(lead.name for lead in db_leads)
            # Get data from DB
            for lead in db_leads:
                email = LeadEmails.objects.filter(lead=lead).first()
                phone = LeadPhoneNumbers.objects.filter(lead=lead).first()
                contact = LeadContactNames.objects.filter(lead=lead).first()
                results.append({
                    'company': lead.name,
                    'email': email.value if email else '',
                    'phone': phone.value if phone else '',
                    'contact_name': contact.value if contact else ''
                })
            # Companies not found in DB
            not_found = [c for c in company_list if c not in db_lead_names]
            # if not_found:
                # deepseek_results = get_deepseek_data(not_found)
                # for name in not_found:
                    # info = deepseek_results.get(name, {})
                    # results.append({
                    #     'company': name,
                    #     'email': info.get('email', ''),
                    #     'phone': info.get('phone', ''),
                    #     'contact_name': info.get('contact_name', '')
                    # })
    else:
        form = CompanyListForm()
    return render(request, 'ai_agent/index.html', {'form': form, 'results': results})
