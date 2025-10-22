from celery import shared_task
from .utils import orchestrate_enrichment_workflow, save_excel_for_task
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
    # Ensure required DB fields that may not have DB defaults are set explicitly
    owner_name = 'IBH'

    task = EnrichmentTask.objects.create(
        task_id=task_id,
        excel_sheet_name=excel_sheet_name,
        status='IN_PROGRESS',
        is_result_downloaded=False,
        owner=owner_name,
        company_count=len(company_names),
    )

    total_companies = len(company_names)

    enriched_results = None

    try:
        # The entire list is passed to the workflow, which handles batching internally.
        enriched_results = orchestrate_enrichment_workflow(company_names, settings.GEMINI_API_KEY, task)

        # Progress is now updated inside the workflow, but we'll set it to 100 at the end.
        task.progress = 100

        if enriched_results:
            task.results = json.dumps(enriched_results)
            # Save excel to disk and attach to task
            try:
                saved_path = save_excel_for_task(task, enriched_results, sheet_name=excel_sheet_name)
                print(f"Saved excel for task {task.task_id} -> {saved_path}")
                # Only mark as SUCCESS if the file was saved
                task.status = 'SUCCESS'
            except Exception as save_exc:
                # If saving the excel fails, the entire task is a failure.
                print(f"Error: failed to save excel for task {task.task_id}: {save_exc}")
                task.status = 'FAILURE'
        else:
            # If no results are returned, but no exception was thrown, it's still a failure.
            task.status = 'FAILURE'

    except Exception as e:
        # Attempt to preserve partial results (if any) and always try to write an Excel
        task.status = 'FAILURE'

        # If orchestrate_enrichment_workflow returned partial results before crashing, use them
        if enriched_results and isinstance(enriched_results, list) and len(enriched_results) > 0:
            results_to_save = enriched_results
            task.results = json.dumps(results_to_save)
        else:
            # No partial results - create a small sheet containing the error message
            results_to_save = [{
                'company_name': 'ENRICHMENT_ERROR',
                'domain': None,
                'phone': None,
                'time_zone': None,
                'email': None,
                'key_personnel': {'name': None, 'phone': None, 'title': None, 'email': None},
                'error': str(e)
            }]
            task.results = json.dumps({'error': str(e)})

        # Try to save whatever we have to an Excel file so users can download diagnostics
        try:
            saved_path = save_excel_for_task(task, results_to_save, sheet_name=excel_sheet_name)
            print(f"Saved fallback excel for task {task.task_id} -> {saved_path}")
        except Exception as save_exc:
            # Log but continue; we don't want the worker to crash here
            print(f"Error saving fallback excel for task {task.task_id}: {save_exc}")

    finally:
        # Ensure completion time is always set.
        task.completed_at = timezone.now()
        task.save()

    return f"Enrichment complete for {excel_sheet_name}"
