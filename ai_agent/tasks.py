from celery import shared_task, group, chain
from .utils import orchestrate_enrichment_workflow, save_excel_for_task
from .models import EnrichmentTask
import json
from django.conf import settings
from django.utils import timezone
import math
from django.db import transaction
from django.db.models import F

# Define the size of each chunk
CHUNK_SIZE = 20

@shared_task(bind=True)
def enrich_chunk_task(self, company_names, task_id):
    """
    Celery task to process a small chunk of companies and update progress.
    """
    task = EnrichmentTask.objects.get(task_id=task_id)
    
    try:
        enriched_results = orchestrate_enrichment_workflow(company_names, settings.GEMINI_API_KEY, task)
    finally:
        # This block ensures that progress is updated even if the workflow fails.
        # We use an F() expression to atomically increment the counter in the database,
        # which prevents race conditions without needing select_for_update.
        task_to_update = EnrichmentTask.objects.get(task_id=task_id)
        task_to_update.chunks_completed = F('chunks_completed') + 1
        task_to_update.save(update_fields=['chunks_completed'])
        task_to_update.refresh_from_db()

        # Calculate and save the new progress percentage
        if task_to_update.total_chunks > 0:
            progress_percentage = int((task_to_update.chunks_completed / task_to_update.total_chunks) * 100)
            task_to_update.progress = progress_percentage
            task_to_update.save(update_fields=['progress'])

    return enriched_results

@shared_task(bind=True)
def collect_results_task(self, results, task_id):
    """
    Celery task to collect results from all chunks, generate the Excel file,
    and finalize the main task.
    """
    task = EnrichmentTask.objects.get(task_id=task_id)
    
    # Flatten the list of lists into a single list of results
    final_results = [item for sublist in results for item in sublist]
    
    try:
        # Generate the Excel file in memory
        excel_content = save_excel_for_task(task, final_results, sheet_name=task.excel_sheet_name)
        # Save the binary content to the database
        task.results_file_content = excel_content
        task.status = 'SUCCESS'
        task.progress = 100
    except Exception as e:
        print(f"Error generating or saving Excel content for task {task.task_id}: {e}")
        task.status = 'FAILURE'
    finally:
        task.completed_at = timezone.now()
        task.save()

    return f"Enrichment complete for {task.excel_sheet_name}"

@shared_task(bind=True)
def enrich_data_task(self, company_names, excel_sheet_name):
    """
    Celery task to manage the data enrichment process by breaking it into chunks.
    """
    task_id = self.request.id
    owner_name = 'IBH'
    total_companies = len(company_names)
    total_chunks = math.ceil(total_companies / CHUNK_SIZE)

    task = EnrichmentTask.objects.create(
        task_id=task_id,
        excel_sheet_name=excel_sheet_name,
        status='IN_PROGRESS',
        is_result_downloaded=False,
        owner=owner_name,
        company_count=total_companies,
        total_chunks=total_chunks,
    )

    # Create a group of parallel chunk processing tasks
    chunk_tasks = group(
        enrich_chunk_task.s(company_names[i:i + CHUNK_SIZE], task_id)
        for i in range(0, total_companies, CHUNK_SIZE)
    )

    # Define a chain: run all chunk tasks in parallel, then run the collector task
    # with the results of the chunk tasks.
    workflow = chain(chunk_tasks, collect_results_task.s(task_id=task_id))
    
    # Start the workflow
    workflow.apply_async()

    return f"Enrichment started for {excel_sheet_name}"
