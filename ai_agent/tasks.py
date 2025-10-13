from celery import shared_task
from .utils import orchestrate_enrichment_workflow, generate_excel_response

@shared_task
def enrich_data_task(company_names, excel_sheet_name):
    """
    Celery task to perform data enrichment in the background.
    """
    GEMINI_API_KEY = "AIzaSyBuNSlfHDLXEWfr1GUCsHWoqeLKibEyT0E"
    enriched_results = orchestrate_enrichment_workflow(company_names, GEMINI_API_KEY)
    
    if enriched_results:
        # Since we can't return an HttpResponse from a background task,
        # we'll need to handle the result differently.
        # For now, let's just log that it's done.
        # In a future step, we could save the file and notify the user.
        print(f"Enrichment complete for {len(company_names)} companies. Excel file '{excel_sheet_name}.xlsx' is ready to be generated.")
        # For now, we can't directly return the file to the user.
        # We will need a mechanism to notify the user and provide a download link.
        # This is a more advanced topic involving channels or another notification system.
        # For this implementation, we will just log the completion.
    else:
        print("Enrichment task finished, but no results were generated.")

    return f"Enrichment complete for {excel_sheet_name}"
