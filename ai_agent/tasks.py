from celery import shared_task, chain
from .utils import orchestrate_enrichment_workflow, save_excel_for_task
from .models import EnrichmentTask
from django.conf import settings
from django.utils import timezone
import math
from django.db.models import F

# Define the size of each chunk for sequential processing
CHUNK_SIZE = 20

@shared_task(bind=True)
def enrich_and_pass_chunk_task(self, previous_results, company_names, task_id):
    """
    Processes one chunk of companies, appends results to the previous ones,
    updates progress, and passes the cumulative results to the next task in the chain.
    """
    task = EnrichmentTask.objects.get(task_id=task_id)

    # 1. Enrich the current chunk of companies
    current_results = orchestrate_enrichment_workflow(company_names, settings.GEMINI_API_KEY, task)

    # 2. Combine results safely
    if previous_results is None:
        previous_results = []
    
    # Filter out any non-dictionary items from the current results to prevent errors
    valid_current_results = [res for res in current_results if isinstance(res, dict)]
    combined_results = previous_results + valid_current_results

    # 3. Atomically update the progress in the database
    task.chunks_completed = F('chunks_completed') + 1
    task.save(update_fields=['chunks_completed'])
    task.refresh_from_db()

    if task.total_chunks > 0:
        progress_percentage = int((task.chunks_completed / task.total_chunks) * 100)
        task.progress = progress_percentage
        task.save(update_fields=['progress'])

    # 4. Return the combined results for the next task in the chain
    return combined_results

@shared_task(bind=True)
def finalize_enrichment_task(self, all_results, task_id):
    """
    The final task in the chain. Takes the complete list of results,
    generates the Excel file, and saves it to the database.
    """
    task = EnrichmentTask.objects.get(task_id=task_id)
    try:
        # One final check to ensure all data is valid before file generation
        final_results = [res for res in all_results if isinstance(res, dict)]

        excel_content = save_excel_for_task(task, final_results, sheet_name=task.excel_sheet_name)
        task.results_file_content = excel_content
        task.status = 'SUCCESS'
        task.progress = 100
    except Exception as e:
        print(f"CRITICAL: Final Excel generation failed for task {task.task_id}: {e}")
        task.status = 'FAILURE'
    finally:
        task.completed_at = timezone.now()
        task.save()

    return f"Enrichment complete and finalized for {task.excel_sheet_name}"

@shared_task(bind=True)
def enrich_data_task(self, company_names, excel_sheet_name):
    """
    Manages the data enrichment process by creating a sequential chain of tasks.
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

    chunks = [company_names[i:i + CHUNK_SIZE] for i in range(0, total_companies, CHUNK_SIZE)]

    if not chunks:
        task.status = 'SUCCESS'
        task.progress = 100
        task.completed_at = timezone.now()
        task.save()
        return "No companies to enrich."

    # Build the sequential chain of tasks
    # Start with the first chunk, passing `None` for previous_results
    task_chain = enrich_and_pass_chunk_task.s(None, chunks[0], task_id)

    # For the rest of the chunks, Celery automatically passes the result of the previous task
    for chunk in chunks[1:]:
        task_chain |= enrich_and_pass_chunk_task.s(chunk, task_id)

    # The final task in the chain is the finalizer, which receives all results
    workflow = task_chain | finalize_enrichment_task.s(task_id=task_id)
    
    workflow.apply_async()

    return f"Sequential enrichment started for {excel_sheet_name}"
