from celery import shared_task
from .utils import orchestrate_enrichment_workflow
from .models import EnrichmentTask
import json
from django.conf import settings
from django.utils import timezone

@shared_task(bind=True)
def enrich_data_task(self, company_names, excel_sheet_name):
    """
    Celery task to perform data enrichment in the background.
    """
    task_id = self.request.id
    task = EnrichmentTask.objects.create(
        task_id=task_id,
        excel_sheet_name=excel_sheet_name,
        status='IN_PROGRESS'
    )

    total_companies = len(company_names)
    
    try:
        # The entire list is passed to the workflow, which handles batching internally.
        enriched_results = orchestrate_enrichment_workflow(company_names, settings.GEMINI_API_KEY, task)
        
        # Progress is now updated inside the workflow, but we'll set it to 100 at the end.
        task.progress = 100
        
        if enriched_results:
            task.results = json.dumps(enriched_results)
            task.status = 'SUCCESS'
        else:
            # If no results are returned, but no exception was thrown, it's still a failure.
            task.status = 'FAILURE'
            
    except Exception as e:
        task.status = 'FAILURE'
        task.results = json.dumps({'error': str(e)})
        
    finally:
        # Ensure completion time is always set.
        task.completed_at = timezone.now()
        task.save()

    return f"Enrichment complete for {excel_sheet_name}"
