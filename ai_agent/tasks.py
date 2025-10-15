from celery import shared_task
from .utils import orchestrate_enrichment_workflow
from .models import EnrichmentTask
import json
from django.conf import settings

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

    try:
        enriched_results = orchestrate_enrichment_workflow(company_names, settings.GEMINI_API_KEY)
        
        if enriched_results:
            task.results = json.dumps(enriched_results)
            task.status = 'SUCCESS'
            task.save()
        else:
            task.status = 'FAILURE'
            task.save()
    except Exception as e:
        task.status = 'FAILURE'
        task.results = json.dumps({'error': str(e)})
        task.save()

    return f"Enrichment complete for {excel_sheet_name}"
