
from django.shortcuts import render
from .forms import CompanyListForm
from main.models import Lead, LeadEmails, LeadPhoneNumbers, LeadContactNames
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
def enrich_data(request):
    form = CompanyListForm()
    return render(request, 'ai_agent/enrich.html', {'form': form})




# ############################################################## AI's Part ##############################################################


# # Dummy DeepSeek API endpoint and key (replace with real values)
# DEEPSEEK_API_URL = 'https://api.deepseek.com/company-info'
# DEEPSEEK_API_KEY = 'YOUR_DEEPSEEK_API_KEY'

# # def get_deepseek_data(company_names):
#     # This function should call the DeepSeek API for company names not found in the DB
#     # return results




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