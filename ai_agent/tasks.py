from celery import shared_task, group, chain
from .utils import orchestrate_enrichment_workflow, save_excel_for_task
from .models import EnrichmentTask
from django.conf import settings
from django.utils import timezone
import math
from django.db.models import F

# Define the size of each chunk, allowing override from settings for easier tuning
DEFAULT_CHUNK_SIZE = 20
CHUNK_SIZE = max(
    1,
    int(getattr(settings, "AI_AGENT_CHUNK_SIZE", DEFAULT_CHUNK_SIZE))
)


@shared_task(
    bind=True,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
    retry_jitter=True,
)
def enrich_chunk_task(self, company_names, task_id, show_name=None, category_name=None):
    """
    Processes a single chunk of companies. This task is designed to be fault-tolerant.
    If it fails, Celery will automatically retry it with backoff.
    """
    try:
        task = EnrichmentTask.objects.get(task_id=task_id)
    except EnrichmentTask.DoesNotExist:
        # If the parent task cannot be found, fail fast but don't crash the worker repeatedly
        return []

    # Perform the enrichment for the current chunk
    enriched_results = orchestrate_enrichment_workflow(
        company_names,
        settings.GEMINI_API_KEY,
        task,
        show_name,
        category_name,
    )

    # Atomically update the progress after the chunk is successfully processed.
    # The F() expression creates an atomic database operation, which is safe from race conditions.
    EnrichmentTask.objects.filter(task_id=task_id).update(chunks_completed=F('chunks_completed') + 1)
    task.refresh_from_db()

    if task.total_chunks > 0:
        progress_percentage = int((task.chunks_completed / task.total_chunks) * 100)
        task.progress = progress_percentage
        task.save(update_fields=['progress'])

    return enriched_results

@shared_task(bind=True, acks_late=True)
def finalize_enrichment_task(self, results, task_id):
    """
    The final task. It collects all results, handles potential failures,
    and generates the final Excel file.
    """
    try:
        task = EnrichmentTask.objects.get(task_id=task_id)
    except EnrichmentTask.DoesNotExist:
        # Nothing to finalize if the parent record is gone
        return f"Enrichment task {task_id} no longer exists."

    # Filter out any failed chunks (which may appear as None or exceptions)
    successful_results = [
        item
        for sublist in (results or [])
        if sublist and isinstance(sublist, list)
        for item in sublist
    ]

    try:
        if not successful_results:
            raise ValueError("All enrichment chunks failed.")

        excel_content = save_excel_for_task(task, successful_results, sheet_name=task.excel_sheet_name)
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

@shared_task(bind=True, acks_late=True)
def enrich_data_task(self, company_names, excel_sheet_name, user_id=None, show_name=None, category_name=None, local_found_count=0, **kwargs):
    """
    Manages the data enrichment process by creating a parallel workflow.
    Designed to be robust for very large company lists.
    """
    task_id = self.request.id
    owner_name = 'IBH'
    total_companies = len(company_names or [])

    # Guard against excessively large input to avoid overwhelming worker/broker
    max_companies = int(getattr(settings, "AI_AGENT_MAX_COMPANIES_PER_TASK", 5000))
    if total_companies > max_companies:
        raise ValueError(f"Too many companies in a single enrichment task ({total_companies} > {max_companies}).")

    total_chunks = math.ceil(total_companies / CHUNK_SIZE) if total_companies > 0 else 0

    task = EnrichmentTask.objects.create(
        task_id=task_id,
        excel_sheet_name=excel_sheet_name,
        status='IN_PROGRESS',
        is_result_downloaded=False,
        owner=owner_name,
        company_count=total_companies,
        total_chunks=total_chunks,
        user_id=user_id,
    )

    # Store metadata about how many companies were found locally (so it can be used in the Excel summary)
    try:
        # Allow compatibility: get from explicit param or kwargs if provided by older/newer callers
        local_count = int(local_found_count or 0)
        if 'local_found_count' in kwargs and kwargs.get('local_found_count') is not None:
            try:
                local_count = int(kwargs.get('local_found_count'))
            except Exception:
                pass

        task.results = {'local_companies_found': local_count}
        task.save(update_fields=['results'])
    except Exception:
        # Non-fatal: continue without metadata if something goes wrong
        pass

    if total_companies == 0:
        task.status = 'SUCCESS'
        task.progress = 100
        task.completed_at = timezone.now()
        task.save()
        return "No companies to enrich."

    # Create a group of parallel tasks for each chunk
    chunk_tasks = group(
        enrich_chunk_task.s(company_names[i:i + CHUNK_SIZE], task_id, show_name, category_name)
        for i in range(0, total_companies, CHUNK_SIZE)
    )

    # Define a workflow: run all chunks in parallel (bounded by worker concurrency), then run the finalizer
    workflow = (chunk_tasks | finalize_enrichment_task.s(task_id=task_id))

    workflow.apply_async()

    return f"Parallel enrichment started for {excel_sheet_name}"

