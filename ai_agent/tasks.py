from celery import shared_task
from .utils import orchestrate_enrichment_workflow, generate_excel_response
from .models import EnrichmentTask
import json

@shared_task(bind=True)
def enrich_data_task(self, company_names, excel_sheet_name):
    """
    Celery task to perform data enrichment in the background.
    """
    task_id = self.request.id
    EnrichmentTask.objects.create(
        task_id=task_id,
        excel_sheet_name=excel_sheet_name,
        status='IN_PROGRESS'
    )

    GEMINI_API_KEY = "AIzaSyBuNSlfHDLXEWfr1GUCsHWoqeLKibEyT0E"
    enriched_results = orchestrate_enrichment_workflow(company_names, GEMINI_API_KEY)
    
    task = EnrichmentTask.objects.get(task_id=task_id)
    if enriched_results:
        task.results = json.dumps(enriched_results)
        task.status = 'SUCCESS'
        task.save()
        print(f"Enrichment complete for {len(company_names)} companies. Excel file '{excel_sheet_name}.xlsx' is ready to be generated.")
    else:
        task.status = 'FAILURE'
        task.save()
        print("Enrichment task finished, but no results were generated.")

    return f"Enrichment complete for {excel_sheet_name}"
