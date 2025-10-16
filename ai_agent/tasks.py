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

    total_companies = len(company_names)
    enriched_results = []

    try:
        for i, company_name in enumerate(company_names):
            enriched_results.extend(orchestrate_enrichment_workflow([company_name], settings.GEMINI_API_KEY))
            task.progress = int(((i + 1) / total_companies) * 100)
            task.save()

        if enriched_results:
            task.results = json.dumps(enriched_results)
            task.status = 'SUCCESS'
            task.progress = 100
            task.save()
        else:
            task.status = 'FAILURE'
            task.save()
    except Exception as e:
        task.status = 'FAILURE'
        task.results = json.dumps({'error': str(e)})
        task.save()

    return f"Enrichment complete for {excel_sheet_name}"
