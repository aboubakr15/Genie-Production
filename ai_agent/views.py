from django.shortcuts import render, redirect
from .forms import CompanyListForm
from .models import EnrichmentTask
from datetime import timedelta
from django.contrib.auth.decorators import user_passes_test
from main.custom_decorators import is_in_group
from django.http import HttpResponse
from .utils import *
from django.http import JsonResponse
from .tasks import enrich_data_task
from django.contrib import messages
from django.utils import timezone



@user_passes_test(lambda user: is_in_group(user, "ai_agent"))
def index(request):
    # Get credit information
    credit_stats = get_credit_stats()
    credit_balance = get_credit_balance()
    
    # Calculate expiration date (one month from last reset)
    if credit_balance.last_reset_date:
        expiration_date = credit_balance.last_reset_date + timedelta(days=30)
        days_remaining = (expiration_date - timezone.now()).days
    else:
        expiration_date = None
        days_remaining = 0
    
    context = {
        'credit_balance': credit_balance.get_current_balance(),
        'total_added': credit_stats['total_added_this_month'],
        'total_used': credit_stats['total_used_this_month'],
        'expiration_date': expiration_date,
        'days_remaining': days_remaining,
        'last_reset': credit_balance.last_reset_date,
    }
    
    return render(request, 'ai_agent/index.html', context)


@user_passes_test(lambda user: is_in_group(user, "ai_agent"))
def search_view(request):
    return render(request, 'ai_agent/search.html')


@user_passes_test(lambda user: is_in_group(user, "ai_agent"))
def data_enrichment_view(request):
    if request.method == 'POST':
        form = CompanyListForm(request.POST)
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if form.is_valid():
                company_names = [name.strip() for name in form.cleaned_data['company_names'].splitlines() if name.strip()]
                
                # Additional validation: check if list is empty
                if not company_names:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Please enter at least one company name.'
                    }, status=400)
                
                excel_sheet_name = form.cleaned_data['excel_sheet_name'].strip() or 'Enriched Leads'
                
                # Validate sheet name length
                if len(excel_sheet_name) > 31:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Excel sheet name must be 31 characters or less.'
                    }, status=400)
                
                # Check credits first
                if not use_credits(amount=len(company_names), description="AI Enrichment", user=None):
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Insufficient credits to process the request.'
                    }, status=400)
                
                # Call the Celery task to run in the background
                task = enrich_data_task.delay(company_names, excel_sheet_name)
                
                return JsonResponse({
                    'status': 'success', 
                    'message': f"Enrichment for {len(company_names)} companies has started.", 
                    'job_id': task.id
                })
            else:
                # Return form errors as JSON for AJAX requests
                error_messages = []
                for field, error_list in form.errors.items():
                    field_name = form.fields[field].label or field
                    for error in error_list:
                        error_messages.append(f"{field_name}: {error}")
                
                return JsonResponse({
                    'status': 'error', 
                    'message': '<br>'.join(error_messages)
                }, status=400)
        else:
            # For non-AJAX POST requests, process normally
            if form.is_valid():
                # Handle if needed
                pass
    else:
        form = CompanyListForm()
    
    # Render the template for GET requests
    return render(request, 'ai_agent/enrich.html', {'form': form})



def get_enrichment_status(request, task_id):
    try:
        task = EnrichmentTask.objects.using('global').get(task_id=task_id)
        return JsonResponse({'status': task.status, 'progress': task.progress})
    except EnrichmentTask.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Task not found.'}, status=404)


def download_enrichment_results(request, task_id):
    try:
        task = EnrichmentTask.objects.get(task_id=task_id)
        if task.status == 'SUCCESS':
            results = json.loads(task.results)
            return generate_excel_response(results, task.excel_sheet_name)
        else:
            messages.error(request, "The task is not yet complete, or it has failed.")
            return redirect('ai_agent:data_enrichment')
    except EnrichmentTask.DoesNotExist:
        messages.error(request, "Task not found.")
        return redirect('ai_agent:data_enrichment')

