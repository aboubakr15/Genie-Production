from datetime import datetime
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from .views import *


def orchestrate_enrichment_workflow(company_names, api_key, job_id=None):
    """
    Main workflow that orchestrates the entire enrichment process
    """
    from .utils_progress import set_progress, get_progress  # <-- import here to avoid circular imports

    print(f"🚀 Starting enrichment workflow for {len(company_names)} companies")

    # Initialize or reset progress in Redis
    if job_id:
        set_progress(job_id, {
            'current_batch': 0,
            'total_batches': 0,
            'companies_processed': 0,
            'total_companies': len(company_names),
            'current_phase': 'initial',
            'is_complete': False
        })
    else:
        reset_enrichment_progress()

    # # Step 1: Search in databases first
    # found_leads, not_found_leads = search_databases(company_names)
    # print(f"📊 Database results: {len(found_leads)} found, {len(not_found_leads)} not found")
    
    # # Update progress for database search
    # update_progress(0, 0, len(found_leads), len(company_names), 'database_search')
    

    ## If you wan to disable database search and want to use AI for all companies, uncomment below lines ##
    found_leads = []
    not_found_leads = company_names
    print(f"📊 Database search disabled: {len(found_leads)} found, {len(not_found_leads)} not found")

    # --- Progress update ---
    if job_id:
        progress = get_progress(job_id)
        progress.update({
            'current_phase': 'database_search',
            'companies_processed': len(found_leads),
            'total_companies': len(company_names)
        })
        set_progress(job_id, progress)
    else:
        update_progress(0, 0, len(found_leads), len(company_names), 'database_search')
    #######################################################################################################

    # Step 2: Enrich not found leads with AI
    ai_leads = []
    if not_found_leads:
        print(f"🤖 Enriching {len(not_found_leads)} companies with AI...")
        
        # You can enrich in batches and update progress per batch
        batch_size = 10
        total_batches = (len(not_found_leads) + batch_size - 1) // batch_size

        for batch_num, start in enumerate(range(0, len(not_found_leads), batch_size), start=1):
            batch = not_found_leads[start:start + batch_size]
            print(f"🧩 Processing batch {batch_num}/{total_batches}: {len(batch)} companies")

            # Call your enrichment logic
            enriched_batch = enrich_with_ai(batch, api_key, batch_size=batch_size)
            ai_leads.extend(enriched_batch)

            # Update progress after each batch
            if job_id:
                progress = get_progress(job_id)
                progress.update({
                    'current_phase': 'ai_processing',
                    'current_batch': batch_num,
                    'total_batches': total_batches,
                    'companies_processed': len(found_leads) + len(ai_leads),
                })
                set_progress(job_id, progress)
            else:
                update_progress(batch_num, total_batches, len(found_leads) + len(ai_leads), len(company_names), 'ai_processing')
        
        # Step 3: Save AI results to global database
        if ai_leads:
            save_to_global_database(ai_leads)
    
    # Step 4: Merge all results in original order
    enriched_results = merge_results(company_names, found_leads, ai_leads)
    
    # Step 5: Retry companies missing phone numbers (single retry only)
    enriched_results = retry_missing_phones(enriched_results, api_key)
    
    # --- Mark as complete ---
    if job_id:
        progress = get_progress(job_id)
        progress['is_complete'] = True
        progress['current_phase'] = 'completed'
        set_progress(job_id, progress)
    else:
        mark_complete()
    
    print(f"✅ Enrichment workflow completed. Processed {len(enriched_results)} companies")
    return enriched_results


def generate_excel_response(enriched_results, sheet_name="Enriched Leads"):
    """
    Generate styled Excel file from enriched results with custom sheet name
    """
    # Validate and clean sheet name
    sheet_name = clean_sheet_name(sheet_name) if sheet_name else "Enriched Leads"
    
    # Build output data for Excel
    output_data = []
    for result in enriched_results:
        key_personnel = result.get("key_personnel", {})
        phone_number = result.get("phone", "")
        email = result.get("email", "")
        
        output_data.append({
            "Company Name": result.get("company_name"),
            # "Domain": result.get("domain", ""),
            "Phone Number": phone_number,
            "Time Zone": result.get("time_zone", ""),
            "Email": email,
            "DM Name": key_personnel.get("name", ""),
            "Direct / Cell Number": key_personnel.get("phone", ""),
            "Contact Title": key_personnel.get("title", ""),
            "Contact Email": key_personnel.get("email", ""),
            "_MissingPhone": "MISSING" if not phone_number else "",
            "_MissingEmail": "MISSING" if not email else ""
        })

    output_df = pd.DataFrame(output_data)
    
    # Create Excel file
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Remove flag columns for display
        columns_to_drop = ['_MissingPhone', '_MissingEmail']
        existing_columns_to_drop = [col for col in columns_to_drop if col in output_df.columns]
        
        if existing_columns_to_drop:
            display_df = output_df.drop(columns=existing_columns_to_drop)
        else:
            display_df = output_df
        
        # Write data to Excel
        display_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1, header=False)
        
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#366092',  # Dark blue background
            'font_color': 'white',
            'border': 1,
            'font_size': 12,
            'font_name': 'Arial'
        })
        
        cell_format = workbook.add_format({
            'text_wrap': True,
            'valign': 'top',
            'border': 1,
            'font_size': 10,
            'font_name': 'Arial'
        })
        
        missing_format = workbook.add_format({
            'text_wrap': True,
            'valign': 'top',
            'border': 1,
            'font_size': 10,
            'font_name': 'Arial',
            'font_color': '#FF0000',  # Red color for missing data
            'bg_color': '#FFE6E6'     # Light red background
        })
        
        # Set column widths
        column_widths = {
            'Company Name': 30,
            # 'Domain': 25,
            'Phone Number': 20,
            'Time Zone': 15,
            'Email': 30,
            'DM Name': 25,
            'Direct / Cell Number': 20,
            'Contact Title': 25,
            'Contact Email': 30
        }
        
        # Write headers with formatting
        for col_num, column_name in enumerate(display_df.columns):
            worksheet.write(0, col_num, column_name, header_format)
            # Set column width
            width = column_widths.get(column_name, 15)
            worksheet.set_column(col_num, col_num, width)
        
        # Write data rows with conditional formatting for empty cells
        for row_num, (index, row) in enumerate(display_df.iterrows(), start=1):
            for col_num, value in enumerate(row):
                # Use missing format for empty phone/email fields
                if (display_df.columns[col_num] in ['Phone Number', 'Email', 'Direct / Cell Number', 'Contact Email'] 
                    and not value):
                    worksheet.write(row_num, col_num, value, missing_format)
                else:
                    worksheet.write(row_num, col_num, value, cell_format)
        
        # Add autofilter
        worksheet.autofilter(0, 0, len(display_df), len(display_df.columns) - 1)
        
        # Freeze header row
        worksheet.freeze_panes(1, 0)
        
        # Add summary with improved formatting
        summary_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'font_name': 'Arial'
        })
        
        normal_format = workbook.add_format({
            'font_size': 10,
            'font_name': 'Arial'
        })
        
        summary_row = len(display_df) + 3
        
        # Calculate statistics
        total_companies = len(enriched_results)
        companies_with_phone = len([r for r in enriched_results if r.get('phone')])
        companies_with_email = len([r for r in enriched_results if r.get('email')])
        # companies_with_domain = len([r for r in enriched_results if r.get('domain')])
        
        # Write summary
        worksheet.write(summary_row, 0, "Data Enrichment Summary:", summary_format)
        worksheet.write(summary_row + 1, 0, f"Total Companies Processed: {total_companies}", normal_format)
        worksheet.write(summary_row + 2, 0, f"Companies with Phone: {companies_with_phone} ({companies_with_phone/total_companies*100:.1f}%)", normal_format)
        worksheet.write(summary_row + 3, 0, f"Companies with Email: {companies_with_email} ({companies_with_email/total_companies*100:.1f}%)", normal_format)
        # worksheet.write(summary_row + 4, 0, f"Companies with Domain: {companies_with_domain} ({companies_with_domain/total_companies*100:.1f}%)", normal_format)
        worksheet.write(summary_row + 5, 0, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_format)
        
        # Set summary column width
        worksheet.set_column(0, 0, 35)
    
    buffer.seek(0)

    # Create filename from sheet name
    filename = f"{sheet_name.lower().replace(' ', '_')}.xlsx"
    
    response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
