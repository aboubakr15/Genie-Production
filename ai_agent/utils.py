from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from main.models import *

def get_credit_balance():
    """Get current project credit balance"""
    credit, created = Credits.objects.get_or_create(
        id=1,
        defaults={
            'total_credits_added': 0,
            'total_credits_used': 0
        }
    )
    return credit

def add_credits(amount, description="Credits added", user=None, expires_in_days=30):
    """Add credits to project balance with individual expiry"""
    if amount <= 0:
        raise ValidationError("Amount must be positive")
    
    with transaction.atomic():
        credit = get_credit_balance()
        credit.total_credits_added += amount
        credit.save()
        
        # Set individual expiry for this batch of credits
        expires_at = timezone.now() + timedelta(days=expires_in_days)
        
        CreditHistory.objects.create(
            transaction_type='purchase',
            amount=amount,
            description=description,
            user=user,
            expires_at=expires_at
        )
    
    return credit.get_current_balance()

def use_credits(amount, description="Feature usage", user=None, related_object=None):
    """Use credits from project balance using FIFO (oldest credits first)"""
    if amount <= 0:
        raise ValidationError("Amount must be positive")
    
    with transaction.atomic():
        # Get non-expired credits ordered by expiry (soonest first)
        available_credits = CreditHistory.objects.filter(
            transaction_type='purchase',
            expires_at__gt=timezone.now(),
            amount__gt=0
        ).order_by('expires_at', 'created_at')
        
        total_available = sum(credit.amount for credit in available_credits)
        
        if total_available < amount:
            return False  # Insufficient credits
        
        # Use credits with FIFO method
        remaining_to_use = amount
        credits_used = []
        
        for credit_batch in available_credits:
            if remaining_to_use <= 0:
                break
                
            usable_amount = min(credit_batch.amount, remaining_to_use)
            
            # Reduce the original credit batch
            credit_batch.amount -= usable_amount
            credit_batch.save()
            
            # Record the usage
            history_data = {
                'transaction_type': 'usage',
                'amount': -usable_amount,
                'description': description,
                'user': user
            }
            
            if related_object:
                if isinstance(related_object, Sheet):
                    history_data['sheet'] = related_object
                elif isinstance(related_object, SalesShow):
                    history_data['sales_show'] = related_object
            
            CreditHistory.objects.create(**history_data)
            
            remaining_to_use -= usable_amount
            credits_used.append(usable_amount)
        
        # Update total credits used
        credit = get_credit_balance()
        credit.total_credits_used += amount
        credit.save()
    
    return True

def can_use_feature(cost=1):
    """Check if project has enough non-expired credits for a feature"""
    from django.db.models import Sum
    
    available_credits = CreditHistory.objects.filter(
        transaction_type='purchase',
        expires_at__gt=timezone.now(),
        amount__gt=0
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    return available_credits >= cost

def get_credit_stats():
    """Get complete credit statistics"""
    credit = get_credit_balance()
    
    # Calculate actual available balance (non-expired)
    current_balance = credit.get_current_balance()
    
    return {
        'current_balance': current_balance,
        'total_added_this_month': credit.total_credits_added,
        'total_used_this_month': credit.total_credits_used,
        'last_reset': credit.last_reset_date,
        'net_usage': credit.total_credits_added - credit.total_credits_used
    }

def expire_old_credits():
    """Automatically expire credits that have passed their expiry date"""
    from django.utils import timezone
    
    expired_credits = CreditHistory.objects.filter(
        transaction_type='purchase',
        expires_at__lte=timezone.now(),
        amount__gt=0
    )
    
    total_expired = 0
    for credit in expired_credits:
        # Record expiration
        CreditHistory.objects.create(
            transaction_type='expiration',
            amount=0,
            description=f"Credit expiration: {credit.amount} credits expired",
            user=None
        )
        total_expired += credit.amount
        credit.amount = 0  # Set to zero since expired
        credit.save()
    
    return total_expired

# Keep your existing reset functions but they work differently now
def reset_monthly_counters():
    """Reset monthly counters only (credits now expire individually)"""
    with transaction.atomic():
        credit = get_credit_balance()
        
        # Record reset in history
        if credit.total_credits_added > 0 or credit.total_credits_used > 0:
            CreditHistory.objects.create(
                transaction_type='monthly_reset',
                amount=0,
                description=f"Monthly counter reset - Added: {credit.total_credits_added}, Used: {credit.total_credits_used}"
            )
        
        # Reset counters only (credits expire individually now)
        credit.total_credits_added = 0
        credit.total_credits_used = 0
        credit.last_reset_date = timezone.now()
        credit.save()
    
    return True


## History
def get_credit_history(days=30, transaction_type=None):
    """Get credit history with filters"""
    from django.utils import timezone
    from datetime import timedelta
    
    queryset = CreditHistory.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=days)
    )
    
    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)
    
    return queryset.order_by('-created_at')

def get_monthly_summary():
    """Get summary of current month's credit activity"""
    credit = get_credit_balance()
    history_this_month = CreditHistory.objects.filter(
        created_at__gte=credit.last_reset_date
    ).exclude(transaction_type='monthly_reset')

    # Calculate actual available balance (non-expired)
    current_balance = credit.get_current_balance()
    
    return {
        'balance': current_balance,
        'added_this_month': credit.total_credits_added,
        'used_this_month': credit.total_credits_used,
        'transactions_count': history_this_month.count(),
        'last_reset': credit.last_reset_date
    }


############################################################## Enrichment part ##############################################################
import json, time, re
from typing import Optional, Dict, List
import google.genai as genai
from google.genai import types
import pandas as pd
from io import BytesIO
from django.http import HttpResponse, JsonResponse
from django.core.files.base import ContentFile
from .models import GlobalOrganization, GlobalPhoneNumbers, GlobalEmails, GlobalContactNames
from main.models import Lead, LeadEmails, LeadPhoneNumbers, LeadContactNames
from datetime import datetime

enrichment_progress = {
    'current_batch': 0,
    'total_batches': 0,
    'companies_processed': 0,
    'total_companies': 0,
    'current_phase': 'initial',
    'is_complete': False
}

def get_enrichment_progress(request):
    """API endpoint to get current progress"""
    return JsonResponse(enrichment_progress)

def reset_enrichment_progress():
    """Reset progress for new request"""
    global enrichment_progress
    enrichment_progress = {
        'current_batch': 0,
        'total_batches': 0,
        'companies_processed': 0,
        'total_companies': 0,
        'current_phase': 'initial',
        'is_complete': False
    }

def update_progress(current_batch, total_batches, companies_processed, total_companies, current_phase, task=None):
    """Update progress for frontend and task model"""
    global enrichment_progress
    progress_percentage = 0
    if total_companies > 0:
        progress_percentage = int((companies_processed / total_companies) * 100)

    enrichment_progress.update({
        'current_batch': current_batch,
        'total_batches': total_batches,
        'companies_processed': companies_processed,
        'total_companies': total_companies,
        'current_phase': current_phase,
        'is_complete': False,
        'progress': progress_percentage
    })

    # Also update the task in the database if provided
    if task:
        task.progress = progress_percentage
        task.save()

def mark_complete():
    """Mark processing as complete"""
    global enrichment_progress
    enrichment_progress['is_complete'] = True


def orchestrate_enrichment_workflow(company_names, api_key, task):
    """
    Main workflow that orchestrates the entire enrichment process
    """
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
    update_progress(0, 0, len(found_leads), len(company_names), 'database_search', task=task)
    #######################################################################################################

    # Step 2: Enrich not found leads with AI
    ai_leads = []
    if not_found_leads:
        ai_leads = enrich_with_ai(not_found_leads, api_key, batch_size=5, task=task)
        
        # Step 3: Save AI results to global database
        if ai_leads:
            save_to_global_database(ai_leads)
    
    # Step 4: Merge all results in original order
    enriched_results = merge_results(company_names, found_leads, ai_leads)
    
    # Step 5: Retry companies missing phone numbers (single retry only)
    enriched_results = retry_missing_phones(enriched_results, api_key, batch_size=8, task=task)
    
    # Mark as complete
    mark_complete()
    
    return enriched_results


def search_databases(company_names):
    """
    Search for companies in local and global databases
    Returns: (found_leads, not_found_leads)
    """
    found_leads = []
    not_found_leads = []
    
    for company_name in company_names:
        name = company_name.strip()
        if not name:
            continue

        # Try Local DB first
        lead_data = search_local_database(name)
        if lead_data:
            found_leads.append(lead_data)
            continue

        # Try Global DB second
        lead_data = search_global_database(name)
        if lead_data:
            found_leads.append(lead_data)
            continue

        # Not found in either DB
        not_found_leads.append(name)
        
    return found_leads, not_found_leads


def search_local_database(company_name):
    """Search in local Lead database"""
    local_lead = Lead.objects.filter(name__iexact=company_name).first()
    if not local_lead:
        return None
        
    phone_number = LeadPhoneNumbers.objects.filter(lead=local_lead).first() if LeadPhoneNumbers.objects.filter(lead=local_lead).exists() else None

    return {
        "company_name": local_lead.name,
        "phone": phone_number.value if phone_number else None,
        "time_zone": phone_number.time_zone if phone_number else None,
        "email": LeadEmails.objects.filter(lead=local_lead).first().value if LeadEmails.objects.filter(lead=local_lead).exists() else None,
        "key_personnel": {
            "name": LeadContactNames.objects.filter(lead=local_lead).first().value if LeadContactNames.objects.filter(lead=local_lead).exists() else None,
            "phone": None,
            "title": None,
            "email": None
        }
    }


def search_global_database(company_name):
    """Search in global database"""
    global_org = GlobalOrganization.objects.filter(name__iexact=company_name).first()
    if not global_org:
        return None
        
    return {
        "company_name": global_org.name,
        "domain": getattr(global_org, "primary_domain", None),
        "phone": GlobalPhoneNumbers.objects.filter(organization=global_org).first().value if GlobalPhoneNumbers.objects.filter(organization=global_org).exists() else None,
        "time_zone": GlobalPhoneNumbers.objects.filter(organization=global_org).first().time_zone if GlobalPhoneNumbers.objects.filter(organization=global_org).exists() else None,
        "email": GlobalEmails.objects.filter(organization=global_org).first().value if GlobalEmails.objects.filter(organization=global_org).exists() else None,
        "key_personnel": {
            "name": GlobalContactNames.objects.filter(organization=global_org).first().name if GlobalContactNames.objects.filter(organization=global_org).exists() else None,
            "phone": GlobalContactNames.objects.filter(organization=global_org).first().phone_number if GlobalContactNames.objects.filter(organization=global_org).exists() else None,
            "title": GlobalContactNames.objects.filter(organization=global_org).first().title if GlobalContactNames.objects.filter(organization=global_org).exists() else None,
            "email": GlobalContactNames.objects.filter(organization=global_org).first().email if GlobalContactNames.objects.filter(organization=global_org).exists() else None,
        }
    }


def enrich_with_ai(company_names, api_key, batch_size, task):
    """
    Enrich companies using AI in batches
    """
    results = []
    company_mapping = {name.lower().strip(): name for name in company_names}
    total_batches = (len(company_names) + batch_size - 1) // batch_size
    
    for i in range(0, len(company_names), batch_size):
        batch = company_names[i:i + batch_size]
        batch_mapping = {name.lower().strip(): name for name in batch}
        current_batch = (i // batch_size) + 1
        
        # Update progress
        update_progress(
            current_batch=current_batch,
            total_batches=total_batches,
            companies_processed=len(results),
            total_companies=len(company_names),
            current_phase='ai_processing',
            task=task
        )
        
        print(f"🔍 Processing AI batch {current_batch} with {len(batch)} companies")
        
        # Increment request count for the task
        task.request_count += 1
        task.save()

        ai_batch = ai_search_batch(
            batch,
            api_key,
            batch_number=current_batch,
            retry_round=1,
            company_mapping=batch_mapping
        )
        
        if ai_batch:
            results.extend(ai_batch)
        else:
            print(f"❌ AI batch {current_batch} failed, creating empty results")
            # Create empty results for failed batch
            for company in batch:
                results.append({
                    "company_name": company,
                    "domain": None,
                    "phone": None,
                    "time_zone": None,
                    "email": None,
                    "key_personnel": {"name": None, "phone": None, "title": None, "email": None}
                })
        
        # Add delay between batches to avoid rate limiting (except for last batch)
        if i + batch_size < len(company_names):
            print(f"⏳ Waiting 2 seconds before next batch...")
            time.sleep(2)
    
    return results


def ai_search_batch(company_list: List[str], api_key: str, batch_number: int, retry_round: int, company_mapping: Dict[str, str]) -> Optional[List[Dict]]:
    
    # Use original company names for the prompt
    original_company_list = [company_mapping.get(comp.lower().strip(), comp) for comp in company_list]
    company_list_str = "\n".join([f"- {company}" for company in original_company_list])
    
    print(f"🔍 Preparing API request for batch {batch_number} (Retry round {retry_round})...")

    # Enhanced prompt with stricter instructions to prevent cumulative responses
    prompt = f"""You are a business intelligence agent tasked with retrieving verified contact data for {len(company_list)} companies.

    === NON-NEGOTIABLE RULES ===
    1. Process companies SEQUENTIALLY using grounding_with_google_search tool
    2. Return company names EXACTLY as provided - zero modifications
    3. Return ONE JSON object per company in INPUT ORDER
    4. Missing data = null (never guess, infer, or fabricate)
    5. Return ONLY final JSON array - no progress updates, explanations, or markdown
    6. Watch for similar company names - ensure correct matching using grounding tool
    7. Return only one value per field - no arrays or multiple entries separated by commas
    8. Array must contain exactly {len(company_list)} objects

    === PHONE NUMBER PRIORITY (CRITICAL) ===
    **MANDATORY**: If phone field contains any value (including toll-free), time_zone MUST NOT be null

    **DIRECT US LINES FIRST**: Prioritize standard geographic numbers (216-xxx-xxxx, 515-xxx-xxxx, 310-xxx-xxxx, etc.)
    Toll-free (800/888/877/866/855/844/833) are LAST RESORT ONLY if no direct line exists.

    Search order:
    1. Company website (all pages, not just contact, find address)
    2. Google Knowledge Panel (map location sidebar, find address)
    3. Company Facebook page (thoroughly check about section for address)
    4. LinkedIn, Crunchbase (find HQ address)

    === TIME ZONE RULES (REVISED) ===
    **US PHONE NUMBERS** (including +1 numbers):
    - Area codes 201, 202, 203, 212, 215, 216, 217, 218, 219, 224, 225, 228, 229, 231, 234, 239, 240, 248, 251, 252, 253, 254, 256, 260, 262, 267, 269, 270, 272, 274, 276, 281, 283, 301, 302, 303, 304, 305, 307, 308, 309, 310, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 323, 325, 330, 331, 332, 334, 336, 337, 339, 340, 346, 347, 351, 352, 360, 361, 364, 380, 385, 386, 401, 402, 404, 405, 406, 407, 408, 409, 410, 412, 413, 414, 415, 417, 419, 423, 424, 425, 434, 435, 440, 442, 443, 445, 447, 448, 458, 463, 464, 469, 470, 475, 478, 479, 480, 484, 501, 502, 503, 504, 505, 507, 508, 509, 510, 512, 513, 515, 516, 517, 518, 520, 530, 531, 534, 539, 540, 541, 551, 557, 559, 561, 562, 563, 564, 567, 570, 571, 573, 574, 575, 580, 585, 586, 601, 602, 603, 605, 606, 607, 608, 609, 610, 612, 614, 615, 616, 617, 618, 619, 620, 623, 626, 627, 628, 629, 630, 631, 636, 640, 641, 646, 650, 651, 657, 659, 660, 661, 662, 667, 669, 670, 671, 678, 679, 680, 681, 682, 684, 689, 701, 702, 703, 704, 706, 707, 708, 712, 713, 714, 715, 716, 717, 718, 719, 720, 724, 725, 726, 727, 730, 731, 732, 734, 737, 740, 743, 747, 754, 757, 760, 762, 763, 764, 765, 769, 770, 772, 773, 774, 775, 779, 781, 785, 786, 787, 801, 802, 803, 804, 805, 806, 808, 810, 812, 813, 814, 815, 816, 817, 818, 820, 826, 828, 830, 831, 832, 835, 838, 839, 840, 843, 845, 847, 848, 850, 854, 856, 857, 858, 859, 860, 862, 863, 864, 865, 870, 872, 878, 901, 903, 904, 906, 907, 908, 909, 910, 912, 913, 914, 915, 916, 917, 918, 919, 920, 925, 927, 928, 929, 930, 931, 934, 936, 937, 938, 939, 940, 941, 943, 945, 947, 948, 949, 951, 952, 954, 956, 957, 959, 970, 971, 972, 973, 975, 978, 979, 980, 984, 985, 986, 989 → 'est'
    - Area codes 205, 210, 214, 217, 219, 224, 225, 228, 229, 251, 256, 260, 262, 270, 272, 281, 309, 312, 314, 316, 317, 318, 319, 320, 321, 325, 331, 337, 346, 347, 351, 352, 361, 364, 385, 402, 404, 405, 406, 407, 408, 409, 410, 412, 413, 414, 417, 419, 423, 424, 425, 430, 432, 434, 435, 440, 443, 445, 447, 458, 463, 464, 469, 470, 475, 478, 479, 480, 484, 501, 502, 503, 504, 505, 507, 508, 509, 510, 512, 513, 515, 516, 517, 518, 520, 530, 531, 534, 539, 540, 541, 551, 557, 559, 561, 562, 563, 564, 567, 570, 571, 573, 574, 575, 580, 585, 586, 601, 602, 603, 605, 606, 607, 608, 609, 610, 612, 614, 615, 616, 617, 618, 619, 620, 623, 626, 627, 628, 629, 630, 631, 636, 640, 641, 646, 650, 651, 657, 659, 660, 661, 662, 667, 669, 670, 671, 678, 679, 680, 681, 682, 684, 689, 701, 702, 703, 704, 706, 707, 708, 712, 713, 714, 715, 716, 717, 718, 719, 720, 724, 725, 726, 727, 730, 731, 732, 734, 737, 740, 743, 747, 754, 757, 760, 762, 763, 764, 765, 769, 770, 772, 773, 774, 775, 779, 781, 785, 786, 787, 801, 802, 803, 804, 805, 806, 808, 810, 812, 813, 814, 815, 816, 817, 818, 820, 826, 828, 830, 831, 832, 835, 838, 839, 840, 843, 845, 847, 848, 850, 854, 856, 857, 858, 859, 860, 862, 863, 864, 865, 870, 872, 878, 901, 903, 904, 906, 907, 908, 909, 910, 912, 913, 914, 915, 916, 917, 918, 919, 920, 925, 927, 928, 929, 930, 931, 934, 936, 937, 938, 939, 940, 941, 943, 945, 947, 948, 949, 951, 952, 954, 956, 957, 959, 970, 971, 972, 973, 975, 978, 979, 980, 984, 985, 986, 989 → 'cen'
    - Area codes 206, 208, 209, 213, 253, 310, 323, 360, 408, 415, 424, 425, 442, 458, 503, 509, 510, 530, 559, 562, 619, 626, 627, 628, 650, 657, 661, 669, 678, 707, 714, 747, 760, 764, 769, 775, 778, 805, 818, 831, 858, 909, 916, 925, 935, 949, 951, 971 → 'pac'

    **CANADA PHONE NUMBERS** (+1 numbers):
    - Area codes 204, 226, 236, 249, 250, 263, 289, 306, 343, 365, 367, 368, 403, 416, 418, 431, 437, 438, 450, 467, 474, 506, 514, 519, 548, 579, 581, 587, 600, 604, 613, 639, 647, 672, 678, 705, 709, 742, 753, 778, 780, 782, 807, 819, 825, 867, 873, 902, 905 → Use US mapping above

    **TOLL-FREE NUMBERS** (800, 888, 877, 866, 855, 844, 833):
    - If company has US presence → 'est' (default)
    - If company is Canada-only → 'cen' 
    - If international → use country name

    **NON-US/NON-CANADA PHONE NUMBERS**:
    - Return country name only (e.g., 'UK', 'Australia', 'Germany')
    - Use 'UK' for United Kingdom

    === DATA VALIDATION ===
    * Never return: fake LinkedIn profiles, guessed emails, fabricated phones, assumed domains.
    * Only return: verified data from credible current sources.
    * If domain exists: mandatory deep website check for address, phone, and email.
    * **Timezone Validation**: A `time_zone` (e.g., "est", "cen", "pac", "UK") may ONLY be present if a `phone` is present.

    === INPUT COMPANIES (process in this exact order) ===
    {company_list_str}

    === OUTPUT FORMAT ===
    Return SINGLE JSON array with this structure per company:
    {{
        "company_name": "EXACT INPUT NAME",
        "domain": "domain or null",
        "phone": "phone number or null",
        "time_zone": "est/cen/pac/country or null",
        "email": "email or null",
        "key_personnel": {{
            "name": "name or null",
            "phone": "phone or null",
            "title": "title or null",
            "email": "email or null"
        }}
    }}

    CRITICAL: One value per field. No arrays, no multiple entries, no text outside JSON."""

    try:
        client = genai.Client(api_key=api_key)
        
    except Exception as e:
        return None

    # Define the grounding tool for web search
    grounding_tool = types.Tool(
        google_search=types.GoogleSearch()
    )

    config = types.GenerateContentConfig(
        temperature=0.0,
        tools=[grounding_tool],
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )

        # Enhanced JSON parsing that handles cumulative responses
        return parse_gemini_response_cumulative_fix(response.text, company_list, company_mapping, batch_number, retry_round)
            
    except Exception as e:
        return None


def save_to_global_database(enriched_results):
    """
    Save AI-enriched results to global database, skipping entries with no contact info.
    """
    organizations_created = 0
    phones_created = 0
    emails_created = 0
    contacts_created = 0
    
    for result in enriched_results:
        company_name = result.get('company_name')
        if not company_name:
            continue

        # Extract contact info
        phone_number = result.get('phone')
        email = result.get('email')
        key_personnel = result.get("key_personnel", {})
        contact_phone = key_personnel.get("phone")
        contact_email = key_personnel.get("email")

        # Check for any valid contact information
        has_contact_info = any([
            phone_number and str(phone_number).strip(),
            email and str(email).strip(),
            contact_phone and str(contact_phone).strip(),
            contact_email and str(contact_email).strip()
        ])

        # If no contact info, skip saving this record
        if not has_contact_info:
            print(f"🚫 Skipping {company_name} due to no contact information.")
            continue
        
        try:
            organization, org_created = GlobalOrganization.objects.get_or_create(
                name=company_name,
                defaults={'primary_domain': result.get('domain')}
            )
            
            if org_created:
                organizations_created += 1
            
            # Update primary domain if not set
            if not organization.primary_domain and result.get('domain'):
                organization.primary_domain = result.get('domain')
                organization.save()
            
            # Store phone numbers
            if phone_number and str(phone_number).strip():
                phone_obj, phone_created = GlobalPhoneNumbers.objects.get_or_create(
                    organization=organization,
                    value=phone_number,
                    defaults={'time_zone': result.get('time_zone')}
                )
                if phone_created:
                    phones_created += 1
            
            # Store emails
            if email and str(email).strip():
                email_obj, email_created = GlobalEmails.objects.get_or_create(
                    organization=organization,
                    value=email
                )
                if email_created:
                    emails_created += 1
            
            # Store contact names
            contact_name = key_personnel.get("name")
            if contact_name and str(contact_name).strip():
                contact_obj, contact_created = GlobalContactNames.objects.get_or_create(
                    organization=organization,
                    name=contact_name,
                    defaults={
                        'title': key_personnel.get("title"),
                        'phone_number': contact_phone,
                        'email': contact_email
                    }
                )
                if contact_created:
                    contacts_created += 1
                    
        except Exception as e:
            print(f"❌ Error storing data for {company_name}: {str(e)}")
            continue


def merge_results(company_names, found_leads, ai_leads):
    """
    Merge database results and AI results in original order
    """
    enriched_results = []
    
    # Create lookup maps
    found_map = {lead['company_name']: lead for lead in found_leads}
    ai_map = {lead['company_name']: lead for lead in ai_leads}
    
    for company_name in company_names:
        if company_name in found_map:
            enriched_results.append(found_map[company_name])
        elif company_name in ai_map:
            enriched_results.append(ai_map[company_name])
        else:
            # Fallback: empty structure
            enriched_results.append({
                "company_name": company_name,
                "domain": None,
                "phone": None,
                "time_zone": None,
                "email": None,
                "key_personnel": {"name": None, "phone": None, "title": None, "email": None}
            })
    
    return enriched_results


def retry_missing_phones(enriched_results, api_key, batch_size, task):
    """
    Retry companies that are missing phone numbers using AI in batches.
    """
    companies_to_retry = []
    for result in enriched_results:
        if not result.get('phone') or str(result.get('phone', '')).strip() == '':
            companies_to_retry.append(result.get('company_name'))

    if not companies_to_retry:
        return enriched_results

    print(f"🔄 Retrying {len(companies_to_retry)} companies missing phone numbers...")
    time.sleep(2)

    # Use the same batching/AI logic as enrich_with_ai
    retry_results = []
    company_mapping = {name.lower().strip(): name for name in companies_to_retry}
    for i in range(0, len(companies_to_retry), batch_size):
        batch = companies_to_retry[i:i + batch_size]
        batch_mapping = {name.lower().strip(): name for name in batch}
        
        # Increment request count for the task
        task.request_count += 1
        task.save()

        ai_batch = ai_search_batch(
            batch,
            api_key,
            batch_number=(i // batch_size) + 1,
            retry_round=2,
            company_mapping=batch_mapping
        )
        if ai_batch:
            retry_results.extend(ai_batch)
            # Save the results from the retry batch to the global database
            save_to_global_database(ai_batch)

    # Update the original results with retry data
    retry_map = {result['company_name']: result for result in retry_results}
    for i, result in enumerate(enriched_results):
        company_name = result.get('company_name')
        if company_name in retry_map:
            retry_phone = retry_map[company_name].get('phone')
            if retry_phone and str(retry_phone).strip():
                enriched_results[i]['phone'] = retry_phone
            
            retry_email = retry_map[company_name].get('email')
            if retry_email and str(retry_email).strip():
                enriched_results[i]['email'] = retry_email

    return enriched_results


def save_excel_for_task(task, enriched_results, sheet_name="Enriched Leads"):
    """Save the generated Excel to MEDIA_ROOT/enrichment_results/<task_id>.xlsx and attach to task.results_file"""
    from django.conf import settings
    import os

    print(f"Debug: Starting save_excel_for_task for task_id={task.task_id}")

    # Ensure the folder exists
    media_dir = getattr(settings, 'MEDIA_ROOT', None)
    if not media_dir:
        raise RuntimeError('MEDIA_ROOT is not configured. Set MEDIA_ROOT in settings.py')
    
    print(f"Debug: MEDIA_ROOT={media_dir}")

    target_dir = os.path.join(media_dir, 'enrichment_results')
    print(f"Debug: target_dir={target_dir}")
    os.makedirs(target_dir, exist_ok=True)

    # Build filename
    safe_name = f"{task.task_id}.xlsx" if task and task.task_id else "default.xlsx"
    print(f"Debug: safe_name={safe_name}")
    file_path = os.path.join(target_dir, safe_name)
    print(f"Debug: file_path={file_path}")

    # Use the Excel generation logic with proper formatting
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Build output data for Excel
        output_data = []
        for result in enriched_results:
            key_personnel = result.get("key_personnel", {})
            phone_number = result.get("phone", "")
            email = result.get("email", "")
            
            dm_name_parts = [
                str(key_personnel.get("name", "") or ""),
                str(key_personnel.get("title", "") or "")
            ]
            dm_name = "/".join(part for part in dm_name_parts if part)

            output_data.append({
                "Company Name": result.get("company_name"),
                "Phone Number": phone_number,
                "Time Zone": result.get("time_zone", ""),
                "Direct / Cell Number": key_personnel.get("phone", ""),
                "Email": email,
                "DM Name": dm_name,
                "Contact Email": key_personnel.get("email", ""),
                "_MissingPhone": "MISSING" if not phone_number else "",
                "_MissingEmail": "MISSING" if not email else ""
            })

        output_df = pd.DataFrame(output_data)

        # Remove flag columns for display
        columns_to_drop = ['_MissingPhone', '_MissingEmail']
        display_df = output_df.drop(columns=[col for col in columns_to_drop if col in output_df.columns])
        
        # Write data to Excel with proper sheet name
        sheet_name = clean_sheet_name(task.excel_sheet_name or sheet_name)
        display_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1, header=False)
        
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#366092',
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
            'font_color': '#FF0000',
            'bg_color': '#FFE6E6'
        })
        
        # Set column widths
        column_widths = {
            'Company Name': 30,
            'Phone Number': 20,
            'Time Zone': 15,
            'Email': 30,
            'DM Name': 25,
            'Direct / Cell Number': 20,
            'Contact Email': 30
        }
        
        # Write headers with formatting
        print("Debug: Writing headers and formatting...")
        for col_num, column_name in enumerate(display_df.columns):
            print(f"Debug: Writing header column {col_num}: {column_name}")
            worksheet.write(0, col_num, column_name, header_format)
            worksheet.set_column(col_num, col_num, column_widths.get(column_name, 15))
            
        # Write data rows with conditional formatting
        print("Debug: Writing data rows...")
        for row_num, (index, row) in enumerate(display_df.iterrows(), start=1):
            for col_num, value in enumerate(row):
                if (display_df.columns[col_num] in ['Phone Number', 'Email', 'Direct / Cell Number', 'Contact Email'] 
                    and not value):
                    print(f"Debug: Writing row {row_num} col {col_num}: {value} (missing)")
                    worksheet.write(row_num, col_num, value, missing_format)
                else:
                    print(f"Debug: Writing row {row_num} col {col_num}: {value}")
                    worksheet.write(row_num, col_num, value, cell_format)
        
        # Add autofilter and freeze header
        worksheet.autofilter(0, 0, len(display_df), len(display_df.columns) - 1)
        worksheet.freeze_panes(1, 0)
        
        # Add summary section
        total_companies = len(enriched_results)
        companies_with_phone = len([r for r in enriched_results if r.get('phone')])
        companies_with_email = len([r for r in enriched_results if r.get('email')])
        
        summary_format = workbook.add_format({'bold': True, 'font_size': 11, 'font_name': 'Arial'})
        normal_format = workbook.add_format({'font_size': 10, 'font_name': 'Arial'})
        
        summary_row = len(display_df) + 3
        worksheet.write(summary_row, 0, "Data Enrichment Summary:", summary_format)
        worksheet.write(summary_row + 1, 0, f"Total Companies Processed: {total_companies}", normal_format)
        worksheet.write(summary_row + 2, 0, f"Companies with Phone: {companies_with_phone} ({companies_with_phone/total_companies*100:.1f}%)", normal_format)
        worksheet.write(summary_row + 3, 0, f"Companies with Email: {companies_with_email} ({companies_with_email/total_companies*100:.1f}%)", normal_format)
        worksheet.write(summary_row + 4, 0, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_format)
        
        worksheet.set_column(0, 0, 35)  # Set summary column width

    buffer.seek(0)

    # Try to save using Django's FileField API so storage backends are respected
    print("Debug: Getting file content from buffer...")
    file_content = buffer.getvalue()
    django_file = ContentFile(file_content)

    try:
        print(f"Debug: Saving file via FileField API. safe_name={safe_name}")
        # Save the file via the FileField and let it save the model (save=True)
        # This uses the configured storage backend.
        task.results_file.save(safe_name, django_file, save=True)
        print(f"Debug: FileField.save completed. task.results_file.name={task.results_file.name}")

        # Ensure the model is persisted to 'global' DB if router requires it
        try:
            print("Debug: Saving task to global database...")
            task.save(using='global')
            print("Debug: Task saved to global database successfully")
        except Exception as db_exc:
            print(f"Debug: Failed to save to global DB, trying default: {db_exc}")
            try:
                task.save()
                print("Debug: Task saved to default database successfully")
            except Exception as db_exc2:
                print(f"Error persisting task after FileField.save for task {task.task_id}: {db_exc2}")

        # Diagnostics: print what was saved and where
        try:
            from django.core.files.storage import default_storage
            stored_name = task.results_file.name
            print(f"Debug: task.results_file.name -> {stored_name}")
            exists_in_storage = False
            try:
                exists_in_storage = default_storage.exists(stored_name)
            except Exception as ds_exc:
                print(f"Warning checking default_storage.exists: {ds_exc}")

            # Try to compute a filesystem path for local storage backends
            try:
                storage_path = default_storage.path(stored_name)
            except Exception:
                storage_path = os.path.join(getattr(__import__('django.conf').conf.settings, 'MEDIA_ROOT'), stored_name)

            print(f"Debug: storage_path -> {storage_path}, exists -> {os.path.exists(storage_path)}, default_storage.exists -> {exists_in_storage}")
        except Exception as diag_exc:
            print(f"Debugging prints failed for task {task.task_id}: {diag_exc}")

        return task.results_file.name

    except Exception as e:
        # Best-effort fallback: try writing directly to disk and set the field
        print(f"Error saving file via FileField for task {task.task_id}: {e}")
        try:
            os.makedirs(target_dir, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(file_content)

            relative_path = os.path.join('enrichment_results', safe_name)
            task.results_file = relative_path
            try:
                task.save(using='global')
            except Exception as db_exc:
                try:
                    task.save()
                except Exception as db_exc2:
                    print(f"Error saving fallback task.results_file to DB for task {task.task_id}: {db_exc} then {db_exc2}")
                    raise

            return relative_path
        except Exception as final_exc:
            print(f"Final failure saving excel for task {task.task_id}: {final_exc}")
            raise


def clean_sheet_name(name):
    """
    Clean sheet name to be Excel-compliant
    Excel sheet names must be <= 200 characters and cannot contain : \ / ? * [ ]
    """
    import re
    # Remove invalid characters
    cleaned = re.sub(r'[\\/*?\[\]:]', '', name)
    # Truncate to 200 characters
    return cleaned[:200]


# Helper functions #

def parse_gemini_response_cumulative_fix(response_text: str, expected_companies: List[str], company_mapping: Dict[str, str], batch_number: int, retry_round: int) -> List[Dict]:
    """Fixed JSON parsing that only takes the final complete response"""
    
    response_text = response_text.strip()
    
    # Method 1: Look for the LARGEST complete JSON array (the final one)
    final_json_array = extract_final_json_array(response_text)
    if final_json_array:
        return validate_and_fix_results(final_json_array, expected_companies, company_mapping, batch_number, retry_round)
    
    # Method 2: Fallback to individual object extraction
    json_objects = extract_json_objects(response_text)
    if json_objects:
        return validate_and_fix_results(json_objects, expected_companies, company_mapping, batch_number, retry_round)
    
    # Method 3: Emergency fallback
    return create_emergency_results(expected_companies, company_mapping)


def extract_final_json_array(text: str) -> Optional[List[Dict]]:
    """
    Extract only the final complete JSON array from cumulative responses.
    Looks for the largest valid JSON array that contains the expected number of companies.
    """
    
    # Split by markdown code blocks to find potential JSON arrays
    code_blocks = re.findall(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    
    if code_blocks:
        
        # Try each code block from last to first (most recent first)
        for code_block in reversed(code_blocks):
            try:
                clean_block = code_block.strip()
                parsed = json.loads(clean_block)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed
            except:
                continue
    
    # If no code blocks or they failed, try to find JSON arrays by bracket matching
    arrays = []
    start_pos = 0
    
    while True:
        start_idx = text.find('[', start_pos)
        if start_idx == -1:
            break
            
        # Find matching closing bracket
        bracket_count = 0
        end_idx = -1
        
        for i in range(start_idx, len(text)):
            if text[i] == '[':
                bracket_count += 1
            elif text[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i
                    break
        
        if end_idx != -1:
            json_str = text[start_idx:end_idx+1]
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, list):
                    arrays.append(parsed)
            except:
                pass
            
            start_pos = end_idx + 1
        else:
            break
    
    if arrays:
        # Return the largest array (most likely the final complete one)
        largest_array = max(arrays, key=len)
        return largest_array
    
    return None


def extract_json_objects(text: str) -> List[Dict]:
    """Extract individual JSON objects from text"""
    
    objects = []
    # Improved pattern to handle nested objects better
    pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    
    matches = re.finditer(pattern, text)
    for match in matches:
        try:
            obj_str = match.group()
            # Clean the string - remove control characters and fix common issues
            obj_str = re.sub(r'[\x00-\x1f\x7f]', '', obj_str)
            obj_str = re.sub(r',\s*}', '}', obj_str)  # Fix trailing commas
            obj_str = re.sub(r',\s*]', ']', obj_str)
            
            obj = json.loads(obj_str)
            if isinstance(obj, dict) and obj.get('company_name'):
                objects.append(obj)
        except:
            continue
    
    return objects


def validate_and_fix_results(parsed_results: List[Dict], expected_companies: List[str], company_mapping: Dict[str, str], batch_number: int, retry_round: int) -> List[Dict]:
    """Validate parsed results and fix any issues"""
        
    valid_results = []
    seen_companies = set()
    
    for result in parsed_results:
        if not isinstance(result, dict):
            continue
            
        company_name = result.get('company_name')
        if not company_name:
            continue
            
        # Normalize company name for comparison
        normalized_name = str(company_name).lower().strip()
        
        # Check if this is a duplicate
        if normalized_name in seen_companies:
            continue
            
        seen_companies.add(normalized_name)
        valid_results.append(result)
    
    # Check if we have the right number of results
    if len(valid_results) != len(expected_companies):
        
        # Create results for missing companies
        missing_companies = []
        for expected in expected_companies:
            expected_normalized = expected.lower().strip()
            found = any(result.get('company_name', '').lower().strip() == expected_normalized for result in valid_results)
            if not found:
                missing_companies.append(expected)
        
        if missing_companies:
            for company in missing_companies:
                original_name = company_mapping.get(company, company)
                valid_results.append({
                    "company_name": original_name,
                    "domain": None,
                    "phone": None,
                    "time_zone": None,
                    "email": None,
                    "key_personnel": {"name": None, "phone": None, "title": None, "email": None}
                })
    
    # Ensure we use original company names
    for result in valid_results:
        current_name = result.get('company_name', '')
        normalized_current = str(current_name).lower().strip()
        if normalized_current in company_mapping:
            original_name = company_mapping[normalized_current]
            if current_name != original_name:
                result['company_name'] = original_name
    
    return valid_results


def create_emergency_results(companies: List[str], company_mapping: Dict[str, str]) -> List[Dict]:
    """Create emergency results when parsing completely fails"""
    
    results = []
    for company in companies:
        original_name = company_mapping.get(company, company)
        results.append({
            "company_name": original_name,
            "domain": None,
            "phone": None,
            "time_zone": None,
            "email": None,
            "key_personnel": {"name": None, "phone": None, "title": None, "email": None}
        })
    
    return results
