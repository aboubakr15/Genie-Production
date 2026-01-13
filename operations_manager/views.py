from django.contrib import messages
from main.models import (Lead, LeadTerminationHistory, UserLeader, Sheet, Lead, LeadContactNames, LeadEmails, LeadPhoneNumbers,
                        UserLeader, SalesShow, Sheet, ReadyShow, PriceRequest, Referral, LeadsColors, Notification)
from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AssignLeadsToLeaderForm
from django.contrib.auth.decorators import user_passes_test
from main.custom_decorators import is_in_group
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from main.custom_decorators import is_in_group
import logging
from django.db.models import OuterRef, Subquery, Q, Count, Max
from django.utils import timezone
from .forms import PriceRequestForm
from django.http import HttpResponseRedirect
from django.db import transaction
from django.views.decorators.http import require_POST


logger = logging.getLogger('custom')

@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def index(request):
    query = request.GET.get('q')
    
    # Get the most recent phone number, email, and contact name
    recent_phone_number = LeadPhoneNumbers.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]
    recent_time_zone = LeadPhoneNumbers.objects.filter(lead=OuterRef('pk')).order_by('-id').values('time_zone')[:1]
    recent_email = LeadEmails.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]
    recent_contact_name = LeadContactNames.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]

    if query:
        leads = Lead.objects.filter(name__icontains=query).order_by("-id")
    else:
        leads = Lead.objects.none()
    
    # Annotate leads with recent contact information
    leads = leads.annotate(
        recent_phone_number=Subquery(recent_phone_number),
        recent_time_zone=Subquery(recent_time_zone),
        recent_email=Subquery(recent_email),
        recent_contact_name=Subquery(recent_contact_name)
    )
    
    page = request.GET.get('page', '')
    paginator = Paginator(leads[:10 * 30], 30)  

    try:
        leads_page = paginator.page(page)
    except PageNotAnInteger:
        leads_page = paginator.page(1)
    except EmptyPage:
        leads_page = paginator.page(paginator.num_pages)

    return render(request, 'operations_manager/index.html', {
        'leads': leads_page,
        'query': query
    })


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def manage_leads_teams(request):
    operations_leaders = User.objects.filter(groups__name="operations_team_leader")

    paginator_operations = Paginator(operations_leaders, 5)  # Show 5 operations team leaders per page

    page_number_operations = request.GET.get('page_operations')
    
    page_operations = paginator_operations.get_page(page_number_operations)

    if request.method == 'POST' and 'remove_member' in request.POST:
        leader_id = request.POST.get('leader_id')
        user_id = request.POST.get('user_id')
        leader = get_object_or_404(User, id=leader_id)
        user = get_object_or_404(User, id=user_id)
        UserLeader.objects.filter(user=user, leader=leader).delete()
        return redirect('operations_manager:manage-leads-teams')  

    context = {
        "operations_team_leader": page_operations,
        "paginator_operations": paginator_operations,
    }

    return render(request, "operations_manager/manage_teams.html", context)


# Assign Each Leads team Member to his Team Leader
@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def assign_lead_to_leader(request):
    if request.method == 'POST':
        form = AssignLeadsToLeaderForm(request.POST)
        
        if form.is_valid():
            user = form.cleaned_data['user']
            leader = form.cleaned_data['leader']

            UserLeader.objects.get_or_create(user=user, leader=leader)

            return redirect('operations_manager:manage-leads-teams') 
    else:
        form = AssignLeadsToLeaderForm()
    
    operations_team_leaders = User.objects.filter(groups__name='operations_team_leader')
    
    context = {
        'form': form,
        'operations_team_leaders': operations_team_leaders,
    }
    
    return render(request, "operations_manager/assign_leads_to_leader.html", context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def sheet_detail(request, sheet_id):
    sheet = get_object_or_404(Sheet, id=sheet_id)
    leads = sheet.leads.all()

    return render(request, "operations_manager/sheet_detail.html", {
        "sheet": sheet,
        "leads": leads,
    })



############################################################################################################################

from .tasks import cut_ready_show_into_sales_shows_task

@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
# Cutting proccess #
####################
def cut_ready_show_into_sales_shows(request, ready_show_id):
    # Trigger background task
    cut_ready_show_into_sales_shows_task.delay(ready_show_id, request.user.id)
    
    messages.info(request, "Cutting process started in the background. You will be notified when complete.")
    return redirect(request.META.get('HTTP_REFERER', 'operations_manager:ready-shows'))

def process_all_ready_shows(request, ready_show_ids):
    """
    Loops through a list of ready_show_ids and triggers the background task for each.
    """
    for ready_show_id in ready_show_ids:
        cut_ready_show_into_sales_shows_task.delay(ready_show_id, request.user.id)


def cut_ready_shows(request):
    if request.method == "POST":
        selected_ready_show_ids = request.POST.getlist('selected_ready_shows')
        
        # Ensure there are selected shows
        if not selected_ready_show_ids:
            messages.warning(request, "No shows selected.")
            return redirect('operations_manager:ready-shows')

        # Process each selected ready show
        process_all_ready_shows(request, selected_ready_show_ids)
        
        messages.info(request, "Selected shows are being processed in the background. You will be notified when complete.")
    else:
        messages.error(request, "Invalid request method.")
    
    return redirect(request.META.get('HTTP_REFERER', 'operations_manager:ready-shows'))

############################################################################################################################


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def sales_shows_by_label(request, label=None):
    if label not in ['EHUB', 'EHUB2', 'EP']:
        label = 'EHUB'

    # Fetch SalesShows by the label of the associated ReadyShow
    sales_shows = SalesShow.objects.filter(label=label)

    # Get all users in the 'Sales' group
    sales_group = Group.objects.get(name='Sales')
    sales_agents = sales_group.user_set.all()

    context = {
        'sales_shows': sales_shows,
        'active_label': label,
        'sales_agents': sales_agents,
    }
    return render(request, 'operations_manager/sales_shows.html', context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def assign_sales_show(request):
    if request.method == 'POST':
        # Retrieve selected show IDs from the form
        show_ids = request.POST.getlist('selected_shows')
        
        # Get the selected agent ID
        agent_id = request.POST.get('agent_id')
        if agent_id:
            agent = get_object_or_404(User, id=agent_id)

            # Loop over each selected show and assign the agent
            for show_id in show_ids:
                show = get_object_or_404(SalesShow, id=show_id)
                show.Agent = agent
                show.save()

    return redirect(request.META.get('HTTP_REFERER', 'operations_manager:sales-shows'))


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def ready_shows_view(request, label=None):
    # If no label is passed, default to 'EHUB'
    if label not in ['EHUB', 'EHUB2', 'EP', 'UK', 'Asia', 'Europe']:
        label = 'EHUB'

    # Get search query
    search_query = request.GET.get('search', '')

    # Filter ReadyShows based on the label and search query
    ready_shows = ReadyShow.objects.filter(
        label=label,
        is_done=False,
        is_archived=False,
        sheet__name__icontains=search_query  # Filter by sheet name
    ).order_by("-id")

    # Pagination
    paginator = Paginator(ready_shows, 60)  # Show 30 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Pass the active label, paginated queryset, and search query to the template
    context = {
        'ready_shows': page_obj,  # Use paginated queryset
        'active_label': label,
        'search_query': search_query,  # Pass search query for use in the template
    }

    return render(request, 'operations_manager/ready_shows.html', context)



@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def done_ready_shows(request, label=None):
    # Default label if not passed
    if label not in ['EHUB', 'EHUB2', 'EP']:
        label = 'EHUB'

    # Get the search query from the request
    search_query = request.GET.get('search', '')

    # Filter Done ReadyShows based on the label and search query
    done_shows = ReadyShow.objects.filter(label=label, is_done=True)
    
    # Apply search filtering (for example, searching by sheet name or lead count)
    if search_query:
        done_shows = done_shows.filter(Q(sheet__name__icontains=search_query)).distinct()

    done_shows = done_shows.order_by("-id")

    # Pagination
    paginator = Paginator(done_shows, 60)  # Show 30 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Pass the active label, paginated queryset, and search query to the template
    context = {
        'done_shows': page_obj,
        'active_label': label,
        'search_query': search_query,
    }

    return render(request, 'operations_manager/done_ready_shows.html', context)


# View for Unassigned Sales Shows
@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def unassigned_sales_shows(request, label='EHUB'):
    # Get the search term from the request
    search_term = request.GET.get('search', '')

    # Filter unassigned shows based on the label and search term
    unassigned_shows = SalesShow.objects.filter(
        Agent__isnull=True, label=label, is_archived=False, is_x=False, is_reassigned=False
    )

    if search_term:
        unassigned_shows = unassigned_shows.filter(
            Q(name__icontains=search_term)  # Adjust 'name' to the relevant field(s)
        )

    unassigned_shows = unassigned_shows.order_by("-id")
    labels = ['EHUB', 'EHUB2', 'EP', 'UK', 'Asia', 'Europe']

    # Pagination
    paginator = Paginator(unassigned_shows, 60)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Prefetch related leads and sheet data for just the current page
    page_shows = list(page_obj.object_list.prefetch_related('leads', 'sheet'))

    # Only calculate timezone counts for labels where it applies
    timezone_counts = {}
    if label not in ['UK', 'Europe', 'Asia']:
        # Get all show IDs for the current page
        show_ids = [show.id for show in page_obj.object_list]
        
        # Get time zone counts from LeadPhoneNumbers for leads in each show
        for show in page_obj.object_list:
            # Get all lead IDs for this show
            lead_ids = show.leads.values_list('id', flat=True)
            
            # Count time zones from LeadPhoneNumbers for these leads
            timezone_data = LeadPhoneNumbers.objects.filter(
                lead_id__in=lead_ids, sheet=show.sheet
            ).values('time_zone').annotate(count=Count('id'))
            
            # Convert to the expected format
            timezone_counts[show.id] = {
                'est': 0,
                'cen': 0,
                'pac': 0
            }
            
            for tz_data in timezone_data:
                time_zone = (tz_data['time_zone'] or '').upper()
                if time_zone == 'EST':
                    timezone_counts[show.id]['est'] = tz_data['count']
                elif time_zone == 'CEN':
                    timezone_counts[show.id]['cen'] = tz_data['count']
                elif time_zone == 'PAC':
                    timezone_counts[show.id]['pac'] = tz_data['count']

    blue_red_leads_counts = {
        show.id: LeadsColors.objects.filter(
            lead__in=show.leads.all(), sheet=show.sheet, color__in=['blue', 'red']
        ).count()
        for show in page_obj.object_list
    }

    # Prepare list of sales agents
    sales_agents = User.objects.filter(
        Q(groups__name__in=['sales_manager', 'sales', 'sales_team_leader'])
    ).distinct()

    context = {
        'unassigned_shows': page_obj,
        'label': label,
        'sales_agents': sales_agents,
        'active_label': label,
        'blue_red_leads_counts': blue_red_leads_counts,
        'timezone_counts': timezone_counts,
        'search_term': search_term,
        'labels': labels,
    }

    return render(request, 'operations_manager/unassigned_sales_shows.html', context)



@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def unassigned_x_sales_shows(request, label='EHUB'):
    # Get the search term from the request
    search_term = request.GET.get('search', '')

    # Filter unassigned shows based on the label and search term
    unassigned_shows = SalesShow.objects.filter(
        Agent__isnull=True, is_archived=False, is_x=True, is_reassigned=False
    )

    if search_term:
        unassigned_shows = unassigned_shows.filter(
            Q(name__icontains=search_term)
        )

    unassigned_shows = unassigned_shows.order_by("-id")

    # Pagination
    paginator = Paginator(unassigned_shows, 60)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get show IDs for the current page
    show_ids = [show.id for show in page_obj]

    # Create dictionaries for timezone counts using the new LeadPhoneNumbers model
    timezone_counts = {}
    if show_ids:
        # Prefetch timezone data for all shows in the page
        from django.db.models import Count
        
        # Get all leads for these shows
        show_leads = {}
        for show in page_obj:
            lead_ids = list(show.leads.values_list('id', flat=True))
            show_leads[show.id] = lead_ids
        
        # Get all timezone data in one query
        all_lead_ids = []
        for lead_ids in show_leads.values():
            all_lead_ids.extend(lead_ids)
        
        if all_lead_ids:
            timezone_data = LeadPhoneNumbers.objects.filter(
                lead_id__in=all_lead_ids, sheet=show.sheet
            ).values('lead_id', 'time_zone').annotate(count=Count('id'))
            
            # Organize timezone data by show
            for show in page_obj:
                timezone_counts[show.id] = {'est': 0, 'cen': 0, 'pac': 0}
                
                # Filter timezone data for this show's leads
                show_lead_ids = show_leads[show.id]
                show_tz_data = [tz for tz in timezone_data if tz['lead_id'] in show_lead_ids]
                
                for tz_data in show_tz_data:
                    time_zone = (tz_data['time_zone'] or '').upper()
                    if time_zone == 'EST':
                        timezone_counts[show.id]['est'] += tz_data['count']
                    elif time_zone == 'CEN':
                        timezone_counts[show.id]['cen'] += tz_data['count']
                    elif time_zone == 'PAC':
                        timezone_counts[show.id]['pac'] += tz_data['count']

    blue_red_leads_counts = {
        show.id: LeadsColors.objects.filter(
            lead__in=show.leads.all(), sheet=show.sheet, color__in=['blue', 'red']
        ).count()
        for show in page_obj
    }

    # Prepare list of sales agents
    sales_agents = User.objects.filter(
        Q(groups__name__in=['sales_manager', 'sales', 'sales_team_leader'])
    ).distinct()

    context = {
        'unassigned_shows': page_obj,
        'label': label,
        'sales_agents': sales_agents,
        'active_label': label,
        'blue_red_leads_counts': blue_red_leads_counts,
        'timezone_counts': timezone_counts,
        'search_term': search_term,
    }

    return render(request, 'operations_manager/unassigned_x_sales_shows.html', context)


# View for Assigned Sales Shows
@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def assigned_sales_shows(request, label='EHUB'):
    # Get the search term from the request
    search_query = request.GET.get('search', '')

    # Filter assigned shows based on label and search query
    assigned_shows = SalesShow.objects.filter(
        Agent__isnull=False,
        label=label,
        is_archived=False, is_reassigned=False
    ).filter(
        Q(name__icontains=search_query) | Q(Agent__username__icontains=search_query)
    ).order_by("is_done", "-id")

    # Pagination
    page_number = request.GET.get('page', 1)  # Get the page number from the request, default to 1
    paginator = Paginator(assigned_shows, 60)
    page_obj = paginator.get_page(page_number)

    context = {
        'assigned_shows': page_obj,  # Pass the paginated shows to the template
        'label': label,
        'active_label': label,
        'search_term': search_query,
    }

    return render(request, 'operations_manager/assigned_sales_shows.html', context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def view_sales_agents(request):
    sales_group = Group.objects.get(name='sales')
    sales_team_leader_group = Group.objects.get(name='sales_team_leader')
    sales_manager_group = Group.objects.get(name='sales_manager')

    # Get all users who belong to one of these groups
    agents = User.objects.filter(groups__in=[sales_group, sales_team_leader_group, sales_manager_group]).distinct()

    context = {
        'agents':agents
    }

    return render(request, "operations_manager/view_agents.html", context)


# For recycling
@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def view_agent_done_shows(request, agent_id):
    agent = get_object_or_404(User, id=agent_id)

    if request.method == 'POST':
        show_id = request.POST.get('show_id')
        show = get_object_or_404(SalesShow, id=show_id, Agent=agent)

        # Recycle the show
        show.is_recycled = True
        show.rec_date = timezone.now()
        show.save()

        messages.success(request, f'Show "{show.name}" has been recycled.')

    # Fetch all done shows for the agent
    shows = SalesShow.objects.filter(is_done=True, Agent=agent, is_recycled=False, is_done_rec=False, is_reassigned=False)
    
    context = {
        'agent': agent,
        'shows': shows
    }

    return render(request, "operations_manager/view_agent_done_shows.html", context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def price_requests_view(request):
    if request.method == 'POST':
        form = PriceRequestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('operations_manager:price_request')
    else:
        form = PriceRequestForm()

    price_requests_list = PriceRequest.objects.all().order_by("-id")
    
    # Set up pagination
    paginator = Paginator(price_requests_list, 20)  # Show 10 requests per page
    page_number = request.GET.get('page')
    price_requests = paginator.get_page(page_number)

    context = {
        'price_requests': price_requests,
        'form': form,
    }
    
    return render(request, 'operations_manager/price_request.html', context)


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def update_price_requests(request):
    if request.method == 'POST':
        for key in request.POST:
            if key.startswith('email_status_'):
                request_id = key.split('_')[2]
                email_status = request.POST[key]
                PriceRequest.objects.filter(id=request_id).update(email_status=email_status)
            elif key.startswith('lead_status_'):
                request_id = key.split('_')[2]
                lead_status = request.POST[key]
                PriceRequest.objects.filter(id=request_id).update(lead_status=lead_status)
        return redirect('operations_manager:price-requests')  # Redirect to the price requests list page
    else:
        return redirect('operations_manager:price-requests')  # Handle non-POST requests


@user_passes_test(lambda user: is_in_group(user, "operations_manager") or is_in_group(user, "sales_manager"))
def manage_referrals(request):
    # Get search query
    search_query = request.GET.get('search', '').strip()
    
    # Get the latest referral for each (lead, sheet) combination using subquery
    # This is much more efficient than loading everything into memory
    latest_referrals = Referral.objects.filter(
        lead__isnull=False,
        sheet__isnull=False
    ).values('lead', 'sheet').annotate(
        latest_date=Max('entry_date')
    )
    
    # Get the actual referral objects that match these latest dates
    referrals_list = Referral.objects.filter(
        lead__isnull=False,
        sheet__isnull=False
    ).filter(
        Q(lead__in=[r['lead'] for r in latest_referrals]) &
        Q(sheet__in=[r['sheet'] for r in latest_referrals])
    ).select_related('lead', 'sheet')  # Optimize foreign key queries
    
    # Further filter to ensure we only get the latest per combination
    unique_refs = {}
    for ref in referrals_list:
        key = (ref.lead.id, ref.sheet.id)
        if key not in unique_refs or ref.entry_date > unique_refs[key].entry_date:
            unique_refs[key] = ref
    
    referrals_list = list(unique_refs.values())
    
    # Apply search filter
    if search_query:
        referrals_list = [
            r for r in referrals_list 
            if search_query.lower() in r.lead.name.lower() or 
               search_query.lower() in r.sheet.name.lower()
        ]
    
    # Sort by entry date descending
    referrals_list.sort(key=lambda x: x.entry_date, reverse=True)
    
    # Paginate
    paginator = Paginator(referrals_list, 30)
    page_number = request.GET.get('page')
    referrals = paginator.get_page(page_number)

    return render(request, 'operations_manager/manage_referrals.html', {
        'referrals': referrals,
        'search_query': search_query,
    })



@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def notifications(request):
    user = request.user
    notifications_for_user = Notification.objects.filter(
        receiver=user).order_by('-created_at')

    # Implement pagination
    page = request.GET.get('page', '')
    # Show 10 notifications per page
    paginator = Paginator(notifications_for_user, 20)

    try:
        notifications_page = paginator.page(page)
    except PageNotAnInteger:
        notifications_page = paginator.page(1)
    except EmptyPage:
        notifications_page = paginator.page(paginator.num_pages)

    return render(request, 'operations_manager/notifications.html', {
        'notifications': notifications_page
    })


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def archive_sales_show(request, show_id):
    if request.method == 'POST':
        show = get_object_or_404(SalesShow, id=int(show_id))
        if show:
            show.is_archived = True
            show.save()
        
        return redirect(request.META.get('HTTP_REFERER', 'operations_manager:assigned-sales-shows'))

@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def archive_sales_show_bulk(request):
    if request.method == 'POST':
        select_all = request.POST.get('select_all') == 'true'
        shows_to_archive = []

        if select_all:
            # Get filters from query params
            label = request.GET.get('label', 'EHUB')
            search_term = request.GET.get('search', '')

            # Reconstruct queryset based on filters
            shows_to_archive = SalesShow.objects.filter(
                Agent__isnull=True,
                is_archived=False,
                is_x=False,
                label=label
            )

            if search_term:
                shows_to_archive = shows_to_archive.filter(name__icontains=search_term)

        else:
            # Fallback to manually selected checkboxes
            selected_shows = request.POST.getlist('selected_shows')
            show_ids = [int(sid) for sid in selected_shows if sid.isdigit()]
            shows_to_archive = SalesShow.objects.filter(id__in=show_ids)

        # Perform archiving
        shows_to_archive.update(is_archived=True)

        return redirect(request.META.get('HTTP_REFERER', 'operations_manager:unassigned-sales-shows'))

@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def archived_sales_shows(request):
    query = request.GET.get('q', '')  # Get search query
    archived_shows = SalesShow.objects.filter(is_archived=True).order_by('-done_date')

    if query:
        archived_shows = archived_shows.filter(name__icontains=query)  # Filter by show name

    # Pagination
    paginator = Paginator(archived_shows, 10)  # Show 10 shows per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'operations_manager/archived_sales_shows.html', {
        'page_obj': page_obj,
        'query': query
    })


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def unarchive_sales_show(request, show_id):
    # Fetch the show by ID
    show = get_object_or_404(SalesShow, id=show_id)
    
    # Update the is_archived field to False (unarchive)
    show.is_archived = False
    show.save()

    # Redirect to the same page (to maintain pagination and filtering)
    referer_url = request.META.get('HTTP_REFERER', 'operations_manager:archived-sales-shows')
    return redirect(referer_url)


@require_POST
@transaction.atomic
@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def reassign_sales_show(request):
    show_id = request.POST.get('show_id')
    if not show_id:
        return redirect(request.META.get('HTTP_REFERER'))

    original_show = get_object_or_404(SalesShow, id=show_id)

    # Create a new show using create(), with copied attributes
    new_show = SalesShow.objects.create(
        name=f"{original_show.name} (Reassigned)",
        sheet=original_show.sheet,
        is_done=False,
        is_recycled=False,
        is_done_rec=False,
        label=original_show.label,
        is_archived=False,
        is_x=original_show.is_x,
        is_reassigned=True,
        is_done_reassigned=False,
    )


    # Copy the leads (ManyToMany)
    new_show.leads.set(original_show.leads.all())

    messages.success(request, f"Show '{original_show.name}' successfully reassigned.")

    return redirect(request.META.get('HTTP_REFERER'))


def reassigned_sales_shows(request):
    search_term = request.GET.get("search", "")
    page_number = request.GET.get("page", 1)

    # Filter only reassigned and unassigned shows
    shows_qs = SalesShow.objects.filter(
        is_reassigned=True,
        Agent__isnull=True
    )

    if search_term:
        shows_qs = shows_qs.filter(name__icontains=search_term)

    shows_qs = shows_qs.order_by("-id")  # Recent first

    paginator = Paginator(shows_qs, 20)  # Show 10 per page
    unassigned_shows = paginator.get_page(page_number)

    context = {
        "unassigned_shows": unassigned_shows,
        "sales_agents": User.objects.filter(groups__name__in=["sales", "sales_team_leader", "sales_manager"]),
        "search_term": search_term,
    }

    return render(request, "operations_manager/reassigned_shows.html", context)


################################### Copied code cuz i am lazy - for archiving shows ###################################

@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def archive_ready_show(request, show_id):
    if request.method == 'POST':
        ready_show = get_object_or_404(ReadyShow, id=show_id)  # Fetch the sheet by ID
        ready_show.is_archived = True  # Mark as archived
        ready_show.save()  # Save the changes to the database
        
        # Get the referring URL or use a fallback
        referer_url = request.META.get('HTTP_REFERER', 'operations_manager:manage-sheets')
        
        # Redirect to the referring URL
        return HttpResponseRedirect(referer_url)
    

@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def archive_ready_show_bulk(request):
    """
    Bulk archive multiple ready shows
    """
    if request.method == 'POST':
        selected_ready_shows = request.POST.getlist('selected_ready_shows')
        
        # Ensure there are selected shows
        if not selected_ready_shows:
            messages.warning(request, "No shows selected.")
            return redirect(request.META.get('HTTP_REFERER', 'operations_manager:ready-shows'))

        # Archive each selected ready show
        for show_id in selected_ready_shows:
            if show_id.isdigit():
                ready_show = get_object_or_404(ReadyShow, id=int(show_id))
                ready_show.is_archived = True
                ready_show.save()
        
        messages.success(request, f"Successfully archived {len(selected_ready_shows)} ready shows.")
    else:
        messages.error(request, "Invalid request method.")
    
    return redirect(request.META.get('HTTP_REFERER', 'operations_manager:ready-shows'))


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def archived_ready_shows(request):
    query = request.GET.get('q', '')  # Get search query
    archived_sheets = ReadyShow.objects.filter(is_archived=True).order_by('-done_date')

    if query:
        archived_sheets = archived_sheets.filter(sheet__name__icontains=query)  # Filter by show name

    # Pagination
    paginator = Paginator(archived_sheets, 60)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'operations_manager/archived_ready_shows.html', {
        'page_obj': page_obj,
        'query': query
    })


@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def unarchive_ready_show(request, show_id):
    # Fetch the sheet by ID
    ready_show = get_object_or_404(ReadyShow, id=show_id)
    
    # Update the is_done field to False (unarchive)
    ready_show.is_archived = False
    ready_show.save()

    # Redirect to the same page (to maintain pagination and filtering)
    referer_url = request.META.get('HTTP_REFERER', 'operations_manager:archived-sheets')
    return redirect(referer_url)

##########################################################################################################################
@user_passes_test(lambda user: is_in_group(user, "operations_manager"))
def view_ready_show(request, show_id):
    show = get_object_or_404(ReadyShow, id=show_id)
    leads = show.leads.all()
    sheet = show.sheet  # to filter phones/emails/names only from the related sheet

    formatted_leads = []
    for lead in leads:
        phone_numbers = list(
            LeadPhoneNumbers.objects.filter(lead=lead, sheet=sheet)
        )
        emails = list(
            LeadEmails.objects.filter(lead=lead, sheet=sheet).values_list('value', flat=True)
        )
        contact_names = list(
            LeadContactNames.objects.filter(lead=lead, sheet=sheet).values_list('value', flat=True)
        )

        formatted_leads.append({
            'company_name': lead.name,
            'phone_numbers': phone_numbers,
            'emails': emails,
            'contact_names': contact_names,
        })

    context = {
        'show': show,
        'leads': formatted_leads
    }

    return render(request, 'operations_manager/view_ready_show.html', context)


