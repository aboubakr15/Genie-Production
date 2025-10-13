from celery import shared_task
from django.core.files.storage import default_storage
import os

from .workflows import orchestrate_enrichment_workflow, generate_excel_response
from .utils_progress import set_progress, get_progress


@shared_task(bind=True)
def run_enrichment_task(self, company_names, api_key, sheet_name, job_id):
    """
    Celery task that orchestrates enrichment and generates the downloadable Excel file.
    """
    # Step 1. Initialize progress in Redis
    set_progress(job_id, {
        'current_batch': 0,
        'total_batches': 0,
        'companies_processed': 0,
        'total_companies': len(company_names),
        'current_phase': 'initial',
        'is_complete': False
    })

    # Step 2. Run the main enrichment process
    results = orchestrate_enrichment_workflow(company_names, api_key, job_id)

    # Step 3. Generate Excel file
    response = generate_excel_response(results, sheet_name)

    # Step 4. Save Excel file temporarily on disk
    os.makedirs("tmp", exist_ok=True)
    filename = f"{sheet_name.lower().replace(' ', '_')}_{job_id}.xlsx"
    file_path = os.path.join("tmp", filename)

    with open(file_path, "wb") as f:
        f.write(response.content)

    # Step 5. Update progress to mark as complete and add download URL
    progress = get_progress(job_id) or {}
    progress.update({
        "is_complete": True,
        "download_url": f"/ai_agent/download/{filename}",
        "current_phase": "completed"
    })
    set_progress(job_id, progress)

    print(f"✅ Task complete. Excel file saved at {file_path}")
    return {"file_path": file_path, "download_url": progress["download_url"]}
