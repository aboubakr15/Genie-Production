from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from main.models import (LeadContactNames, LeadEmails, LeadPhoneNumbers, LeadTerminationCode,
    LeadTerminationHistory, SalesShow, TerminationCode, Lead, LeadsColors, SalesLog, IncomingsCount, Notification)
from django.utils import timezone
from .forms import *
from django.db.models import Count, Sum
from datetime import datetime
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import logging
from main.custom_decorators import is_in_group


logger = logging.getLogger('custom')


@user_passes_test(lambda user: user.groups.filter(name__in=["sales", "sales_team_leader", "sales_manager"]).exists())
def index(request):
    user = request.user  # Assume the user is authenticated
    
    # Get date filter from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Convert to datetime objects if provided
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date = None  # Default to None if not provided

    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d') + timezone.timedelta(days=1)  # Include end date
    else:
        end_date = None  # Default to None if not provided

    # Prospects generated
    prospects_generated = LeadTerminationCode.objects.filter(
        user=user, flag__name__in=['PR', 'CB']
    ).filter(entry_date__range=(start_date, end_date)).count()

    # Incomings
    '''''
    This model is used to count the incomings that have been made since the start of operating on the App,
    so it does not change at the dashboard if the termination code was changed.
    ''''' 
    incomings = IncomingsCount.objects.filter(
        user=user
    ).filter(date__range=(start_date, end_date)).count()

    # Flags (Qualified and Non-Qualified)
    flags_qualified = LeadTerminationCode.objects.filter(
        user=user, flag__name='FL', is_qualified=True
    ).filter(entry_date__range=(start_date, end_date)).count()

    flags_non_qualified = LeadTerminationCode.objects.filter(
        user=user, flag__name='FL', is_qualified=False
    ).filter(entry_date__range=(start_date, end_date)).count()

    # Average #Calls (count of leads in all SalesShow objects for this user)
    avg_calls = SalesShow.objects.filter(Agent=user, is_done=True).filter(
        done_date__range=(start_date, end_date)
    ).aggregate(total_leads=Count('leads'))['total_leads'] or 0

    # CD
    cd_count = LeadTerminationCode.objects.filter(
        user=user, flag__name='CD'
    ).filter(entry_date__range=(start_date, end_date)).count()

    # #Nights
    total_nights = LeadTerminationCode.objects.filter(
        user=user, flag__name='CD'
    ).filter(entry_date__range=(start_date, end_date)).aggregate(total_nights=Sum('num_nights'))['total_nights'] or 0

    context = {
        'prospects_generated': prospects_generated,
        'incomings': incomings,
        'flags_qualified': flags_qualified,
        'flags_non_qualified': flags_non_qualified,
        'total_flags': flags_qualified + flags_non_qualified,
        'avg_calls': avg_calls,
        'cd_count': cd_count,
        'total_nights': total_nights,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    }

    return render(request, 'sales/index.html', context=context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales", "sales_team_leader", "sales_manager"]).exists())
def agent_assigned_shows(request):
    # Fetch the SalesShows assigned to the logged-in user
    assigned_shows = SalesShow.objects.filter(Agent=request.user, is_done=False, is_recycled=False, is_archived=False).order_by('-id')

    group_name = request.user.groups.first().name
    context = {
        'assigned_shows': assigned_shows,
        'group_name':group_name
    }
    return render(request, 'sales/assigned_shows.html', context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales", "sales_team_leader", "sales_manager", "operations_manager"]).exists())
def show_detail(request, show_id, recycle=""):

    role = request.user.groups.first().name
    show = get_object_or_404(SalesShow, id=show_id)

    if role == 'sales':
        if show.Agent != request.user:
            return render(request, '404page.html')  # Redirect to the assigned shows page
    
    # Fetch all termination codes based on user group
    termination_codes = TerminationCode.objects.all() if request.user.groups.first().name in ["sales_manager", "sales_team_leader"] else TerminationCode.objects.exclude(name="IC")

    error_message = None

    # Remove flag leads after save
    leads = show.leads.all()

    if role.lower() == "sales":
        exclude_ids = []

        for lead in leads:
            code = LeadTerminationCode.objects.filter(lead=lead, sales_show=show).last()
            if code is not None and code.flag.name in ["FL", "CD", "IC"]:
                exclude_ids.append(lead.id)
        
        leads = leads.exclude(id__in=exclude_ids)

    
    # Build a list of leads along with their related details
    leads_with_details = []
    for lead in leads:
        phone_numbers = LeadPhoneNumbers.objects.filter(lead=lead, sheet=show.sheet)
        emails = LeadEmails.objects.filter(lead=lead, sheet=show.sheet)
        contact_names = LeadContactNames.objects.filter(lead=lead, sheet=show.sheet)
        lead_color = LeadsColors.objects.filter(lead=lead, sheet=show.sheet).first()
        lead_notes = LeadTerminationCode.objects.filter(lead=lead, sales_show=show).first()
        lead_termination_code = LeadTerminationCode.objects.filter(lead=lead, sales_show=show).order_by("id").last()

        leads_with_details.append({
            'lead': lead,
            'phone_numbers': phone_numbers,
            'emails': emails,
            'contact_names': contact_names,
            'color': lead_color.color if lead_color else None,
            'notes': lead_notes.notes if lead_notes else '',
            'tc': lead_termination_code
        })


    if request.method == 'POST':

        save_termination_codes = request.POST.get('save_termination_codes')
        mark_as_done = request.POST.get('mark_as_done')

        for lead_detail in leads_with_details:
            lead = lead_detail['lead']
            termination_code_id = request.POST.get(f'termination_code_{lead.id}')
            cb_date = request.POST.get(f'cb_date_{lead.id}')
            notes = request.POST.get(f'notes_{lead.id}')

            if termination_code_id:
                termination_code = get_object_or_404(TerminationCode, id=termination_code_id)
                
                if type(cb_date) == str:
                    cb_date = cb_date if cb_date.strip() else None

                LeadTerminationHistory.objects.create(
                    user = request.user,
                    termination_code=termination_code,
                    cb_date=cb_date,
                    lead=lead,
                    show=show,
                    notes = notes
                )

                # Fetch the existing LeadTerminationCode to avoid MultipleObjectsReturned error
                existing_code = LeadTerminationCode.objects.filter(
                    lead=lead, sales_show=show, user=show.Agent
                ).first()

                if existing_code:
                    # Update the existing LeadTerminationCode
                    existing_code.flag = termination_code
                    if cb_date:
                        existing_code.CB_date = cb_date
                    existing_code.notes = notes or ""
                    existing_code.save()
                else:
                    # Create a new LeadTerminationCode
                    LeadTerminationCode.objects.create(
                        lead=lead,
                        sales_show=show,
                        user=show.Agent,
                        flag=termination_code,
                        CB_date=cb_date,
                        notes=notes or ""
                    )

                if termination_code.name == 'IC':
                    IncomingsCount.objects.create(user=show.Agent)

        if save_termination_codes:  # Save changes logic
            if recycle=="recycle":
                return redirect(f'{role}:show-detail-recycle', show_id=show_id, recycle="recycle")
            else:
                return redirect(f'{role}:show-detail', show_id=show_id)

        elif mark_as_done:  # Mark as done logic
            all_termination_codes_selected = all(
                request.POST.get(f'termination_code_{lead_detail["lead"].id}') for lead_detail in leads_with_details
            )

            if all_termination_codes_selected:
                if recycle=="recycle":
                    show.is_done_rec = True
                    show.done_rec_date = timezone.now()
                    show.save()
                    SalesLog.objects.create(
                        message=f"Show {show.name} is marked done from recycle",
                        date=timezone.now(),
                        user=request.user
                    )
                else:
                    show.is_done = True
                    show.done_date = timezone.now()
                    show.save()
                    SalesLog.objects.create(
                        message=f"Show {show.name} is marked done",
                        date=timezone.now(),
                        user=request.user
                    )
                return redirect(f'{role}:assigned-shows')
            else:
                error_message = "You Haven't Finished Dialing The Sheet !!"


    context = {
        'show': show,
        'leads_with_details': leads_with_details,
        'termination_codes': termination_codes,
        'error_message': error_message,
        'recycle':recycle,
        'role':role,
    }


    return render(request, 'sales/show_detail.html', context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales", "sales_team_leader", "sales_manager"]).exists())
def view_saved_leads(request, code_id=None):
    code = get_object_or_404(TerminationCode, name='CB') if code_id is None else get_object_or_404(
        TerminationCode, id=code_id)
    role = request.user.groups.first().name

    allowed = {
        'sales': ['CB', 'PR'],
        'sales_team_leader': ['CB', 'PR', 'CD', 'FL', 'IC'],
        'sales_manager': ['CB', 'PR', 'CD', 'FL', 'IC']
    }

    if role and role in allowed:
        my_allowed = allowed[role]
    else:
        my_allowed = []

    if code.name not in my_allowed:
        return HttpResponseBadRequest()

    termination_codes = TerminationCode.objects.filter(name__in=my_allowed)
    termination_codes_selection = TerminationCode.objects.exclude(name="IC") if role == "sales" else TerminationCode.objects.all()
    
    order_by = request.GET.get('order_by', '-entry_date')  # Default sorting
    
    leads = LeadTerminationCode.objects.filter(user=request.user, flag=code).order_by(order_by)


    if request.method == 'POST':
        for lead_termination in leads:
            lead_id = lead_termination.lead.id
            sales_show_id = lead_termination.sales_show.id
            identifier = f'termination_{lead_id}_{sales_show_id}'  # Create a combined identifier
            termination_code_id = request.POST.get(identifier)
            # Update for new identifier
            status = request.POST.get(f'status_{lead_id}_{sales_show_id}')
            num_rooms = request.POST.get(f'rooms_{lead_id}_{sales_show_id}')
            num_nights = request.POST.get(f'nights_{lead_id}_{sales_show_id}')
            options = request.POST.get(f'options_{lead_id}_{sales_show_id}')
            notes = request.POST.get(f'notes_{lead_id}_{sales_show_id}')
            cb_date = request.POST.get(f'cb_date_{lead_id}_{sales_show_id}')
            is_qualified = request.POST.get(f'is_qualified_{lead_id}_{sales_show_id}') == 'on'

            new_code = None

            if termination_code_id:
                new_code = TerminationCode.objects.get(id=termination_code_id)
                lead_termination.flag = new_code  # Update termination code

            if type(cb_date) == str:
                cb_date = cb_date if cb_date.strip() else None


            # Update other fields
            if status:
                lead_termination.status = status
            if num_rooms:
                lead_termination.num_rooms = int(num_rooms)
            if num_nights:
                lead_termination.num_nights = int(num_nights)
            if options:
                lead_termination.options = options.strip()
            if cb_date:
                lead_termination.CB_date = cb_date
            if notes:
                lead_termination.notes = notes

            latest_termination = LeadTerminationHistory.objects.filter(lead=lead_termination.lead).order_by('-entry_date').first()

            # Only create a new entry if there's a new termination code or callback date
            if latest_termination is None or (
                (new_code is not None and latest_termination.termination_code != new_code) or
                (cb_date is not None and latest_termination.cb_date != cb_date)
                ):
                # Create a new history record if either field has changed
                LeadTerminationHistory.objects.create(
                    termination_code=new_code,
                    cb_date=cb_date,
                    lead=lead_termination.lead,
                    show=lead_termination.sales_show,
                    notes=notes
                )


            lead_termination.is_qualified = is_qualified  # Set the checkbox value
            lead_termination.save()

        return redirect(f'{role}:view-saved-leads', code_id=code.id)

    leads_data = []
    for lead_termination in leads:
        lead = lead_termination.lead
        phones = LeadPhoneNumbers.objects.filter(
            lead=lead, sheet=lead_termination.sales_show.sheet)
        emails = LeadEmails.objects.filter(
            lead=lead, sheet=lead_termination.sales_show.sheet).values_list('value', flat=True)
        contacts = LeadContactNames.objects.filter(
            lead=lead, sheet=lead_termination.sales_show.sheet).values_list('value', flat=True)
        sales_show = lead_termination.sales_show

        # Fetch previous cb dates from LeadTerminationHistory
        previous_cb_dates = LeadTerminationHistory.objects.filter(
            lead=lead, show=sales_show
        ).exclude(cb_date__isnull=True).values_list('cb_date', flat=True).distinct()
    
        previous_cb_dates = sorted(previous_cb_dates)

        leads_data.append({
            'lead': lead,
            'sales_show': lead_termination.sales_show,
            'sales_show_id': lead_termination.sales_show.id,
            'phones': phones,
            'emails': emails,
            'contacts': contacts,
            'termination': lead_termination.flag.full_name,
            'cb_date': lead_termination.CB_date,
            'previous_cb_dates': previous_cb_dates,
            'notes': lead_termination.notes,
            'status': lead_termination.status,
            'num_rooms': lead_termination.num_rooms,
            'num_nights': lead_termination.num_nights,
            'options': lead_termination.options,
            'entry_date': lead_termination.entry_date,
            # 'timezone': lead_termination.lead.time_zone,
            'Agent': sales_show.Agent,
            'is_qualified': lead_termination.is_qualified,  
            'entry_date': lead_termination.entry_date,
        })


    context = {
        'leads_data': leads_data,
        'termination_codes': termination_codes,
        'termination_codes_selection': termination_codes_selection,
        'selected_code': code,
        'role': role
    }

    template_name = "sales/view_saved_leads.html" if code.name in [
        'CB', 'IC'] else "sales_team_leader/view_saved_leads_FL_PR.html"
    return render(request, template_name, context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales", "sales_team_leader", "sales_manager"]).exists())
def view_done_shows(request):
    done_shows = SalesShow.objects.filter(Agent=request.user, is_done=True, is_recycled=False).order_by('-id')

    context = {
        'done_shows': done_shows
    }

    return render(request, "sales/view_done_shows.html", context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales", "sales_team_leader", "sales_manager"]).exists())
def view_recycled_shows(request):
    shows = SalesShow.objects.filter(Agent=request.user, is_recycled=True, is_done_rec=False)

    context = {
        'shows':shows
    }

    return render(request, "sales/view_recycled_shows.html", context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales", "sales_team_leader", "sales_manager"]).exists())
def view_done_recycled_shows(request):
    shows = SalesShow.objects.filter(Agent=request.user, is_recycled=True, is_done_rec=True)

    context = {
        'shows':shows
    }

    return render(request, "sales/view_done_recycled_shows.html", context)


@user_passes_test(lambda user: is_in_group(user, 'sales'))
def sales_notifications(request):
    user = request.user
    notifications_for_user = Notification.objects.filter(
        receiver=user).order_by('-created_at')

    page = request.GET.get('page', '')
    paginator = Paginator(notifications_for_user, 10)

    try:
        notifications_page = paginator.page(page)
    except PageNotAnInteger:
        notifications_page = paginator.page(1)
    except EmptyPage:
        notifications_page = paginator.page(paginator.num_pages)

    return render(request, 'sales/notifications.html', {
        'notifications': notifications_page
    })



# @user_passes_test(lambda user: user.groups.filter(name__in=["sales", "sales_team_leader", "sales_manager"]).exists())
# def search(request):
#     if request.method == 'GET':
#         return render(request, "sales/search.html")

#     leads_with_shows = []  # List to hold leads with their corresponding shows
#     if request.method == 'POST':
#         query = request.POST.get('query')
#         sales_agent = request.user

#         # Get the shows for the current sales agent
#         shows = SalesShow.objects.filter(Agent=sales_agent)

#         # Find leads by name first
#         leads_by_name = Lead.objects.filter(sales_shows__in=shows).filter(
#             name__icontains=query).distinct()

#         # Now search for leads by phone number
#         phone_numbers = LeadPhoneNumbers.objects.filter(value__icontains=query, sheet__in=shows.values('sheet'))
#         leads_by_phone = Lead.objects.filter(id__in=phone_numbers.values('lead_id')).distinct()

#         # Combine leads found by name and phone number
#         leads = leads_by_name.union(leads_by_phone)

#         # For each lead, find its associated shows
#         for lead in leads:
#             associated_shows = lead.sales_shows.filter(Agent=sales_agent)
#             for show in associated_shows:
#                 leads_with_shows.append((lead, show))

#         # Pagination
#         paginator = Paginator(leads_with_shows, 10)  # Show 10 leads per page
#         page_number = request.GET.get('page')
#         page_obj = paginator.get_page(page_number)

#         context = {
#             'leads_with_shows': page_obj,
#             'query': query,
#         }
#         return render(request, "sales/search.html", context)

#     else:
#         leads_with_shows = None
#         context = {
#             'leads_with_shows': leads_with_shows,
#         }

#     return render(request, "sales/search.html", context)

