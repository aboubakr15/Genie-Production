from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import Group, User
from django.contrib import messages
from main.custom_decorators import is_in_group
from main.models import (LeadEmails, LeadContactNames, LeadPhoneNumbers, SalesTeams, TerminationCode, UserLeader,
                        LeadTerminationCode, SalesShow, LeadTerminationHistory, Lead, Notification, IncomingsCount, FlagsCount)
from django.db.models import Count, Sum, OuterRef, Subquery, Prefetch
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.decorators import user_passes_test, login_required
from sales_manager.forms import AssignSalesToLeaderForm
from datetime import datetime
from django.utils import timezone


@user_passes_test(lambda user: is_in_group(user, "sales_manager"))
def index(request):
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

    # Prospects Generated
    prospects_generated = LeadTerminationCode.objects.filter(
        flag__name__in=['PR', 'CB']
    ).filter(entry_date__range=(start_date, end_date)).count()

    # Incomings
    '''''
    This model is used to count the incomings that have been made since the start of operating on the App,
    so it does not change at the dashboard if the termination code was changed.
    ''''' 
    incomings = IncomingsCount.objects.filter(date__range=(start_date, end_date)).count()

    # Flags (Qualified and Non-Qualified)
    flags_qualified = FlagsCount.objects.filter(
        is_qualified=True
    ).filter(date__range=(start_date, end_date)).count()

    flags_non_qualified = FlagsCount.objects.filter(
        is_qualified=False
    ).filter(date__range=(start_date, end_date)).count()

    total_flags = flags_qualified + flags_non_qualified

    # Avg. #Calls
    avg_calls = SalesShow.objects.filter(
        is_done=True
    ).filter(done_date__range=(start_date, end_date)).aggregate(total_leads=Count('leads'))['total_leads'] or 0

    # CD Count
    cd_count = LeadTerminationCode.objects.filter(
        flag__name='CD'
    ).filter(entry_date__range=(start_date, end_date)).count()

    # Total #Nights
    total_nights = LeadTerminationCode.objects.filter(
        flag__name='CD'
    ).filter(entry_date__range=(start_date, end_date)).aggregate(total_nights=Sum('num_nights'))['total_nights'] or 0

    return render(request, "sales_manager/index.html", {
        "prospects_generated": prospects_generated,
        "incomings": incomings,
        "total_flags": total_flags,
        "flags_qualified": flags_qualified,
        "avg_calls": avg_calls,
        "cd_count": cd_count,
        "total_nights": total_nights,
        "start_date": start_date.strftime('%Y-%m-%d') if start_date else '',
        "end_date": end_date.strftime('%Y-%m-%d') if end_date else '',
    })


@user_passes_test(lambda user: is_in_group(user, "sales_manager"))
def assign_sales_to_leader(request):
    if request.method == 'POST':
        form = AssignSalesToLeaderForm(request.POST)
        
        if form.is_valid():
            user = form.cleaned_data['user']
            leader = form.cleaned_data['leader']

            UserLeader.objects.get_or_create(user=user, leader=leader)

            return redirect('sales_manager:manage-sales-teams') 
    else:
        form = AssignSalesToLeaderForm()
    
    sales_manager = User.objects.filter(groups__name='sales_manager')
    
    context = {
        'form': form,
        'sales_manager': sales_manager,
    }
    
    return render(request, "sales_manager/assign_sales_to_leader.html", context)


@user_passes_test(lambda user: is_in_group(user, "sales_manager"))
def manage_sales_teams(request):
    sales_leaders = User.objects.filter(groups__name="sales_team_leader")
    paginator_sales = Paginator(sales_leaders, 5)
    page_number_sales = request.GET.get('page_sales')
    page_sales = paginator_sales.get_page(page_number_sales)

    if request.method == 'POST':
        if 'assign_team' in request.POST:
            leader_id = request.POST.get('leader_id')
            team_label = request.POST.get('team_label')
            leader = get_object_or_404(User, id=leader_id)
            
            if SalesTeams.objects.filter(label=team_label).count() > 0:
                messages.error(request, f"This team '{team_label}' is already assigned to a leader")
            else:
                SalesTeams.objects.update_or_create(
                    leader=leader, defaults={'label': team_label}
                )
            return redirect('sales_manager:manage-sales-teams')

        if 'remove_member' in request.POST:
            leader_id = request.POST.get('leader_id')
            user_id = request.POST.get('user_id')
            leader = get_object_or_404(User, id=leader_id)
            user = get_object_or_404(User, id=user_id)
            UserLeader.objects.filter(user=user, leader=leader).delete()
            return redirect('sales_manager:manage-sales-teams')

        if 'assign_opener_closer' in request.POST:
            leader_id = request.POST.get('leader_id')
            user_id = request.POST.get('opener_closer_user')
            leader = get_object_or_404(User, id=leader_id)
            user = get_object_or_404(User, id=user_id)

            # Add the user as an opener/closer for the leader's team
            team = SalesTeams.objects.filter(leader=leader).first()
            if team:
                team.openers_closers.add(user)
                messages.success(request, f"User '{user.username}' assigned as opener/closer.")
            else:
                messages.error(request, "No team found for this leader.")

            return redirect('sales_manager:manage-sales-teams')

    # Fetch the current team for each leader
    current_teams = {leader.id: SalesTeams.objects.filter(leader=leader).first() for leader in page_sales}
    all_users = User.objects.filter(groups__name="sales_team_leader")  # List users not in the leader group

    context = {
        "sales_leaders": page_sales,
        "paginator_sales": paginator_sales,
        "team_labels": SalesTeams.LABEL_CHOICES,
        "current_teams": current_teams,
        "all_users": all_users,  # Pass all users to the template
    }
    return render(request, "sales_manager/manage_teams.html", context)


@user_passes_test(lambda user: is_in_group(user, "sales_manager"))
def view_teams_prospect(request):
    teams = SalesTeams.objects.all()
    default_code = TerminationCode.objects.get(name="CB").id

    context = {
        'teams': teams,
        'default_code':default_code
    }

    return render(request, 'sales_manager/view_teams_prospect.html', context)


@user_passes_test(lambda user: is_in_group(user, "sales_manager"))
def view_teams_shows(request):
    teams = SalesTeams.objects.all()

    context = {
        'teams': teams,
    }

    return render(request, "sales_manager/view_teams_shows.html", context)


@user_passes_test(lambda user: is_in_group(user, "sales_manager"))
def view_teams_shows_recycled(request):
    teams = SalesTeams.objects.all()

    context = {
        'teams': teams,
    }

    return render(request, "sales_manager/view_teams_shows_recycled.html", context)


@user_passes_test(lambda user: is_in_group(user, "sales_manager"))
def leads_inventory(request):
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

    return render(request, 'sales_manager/leads_inventory.html', {
        'leads': leads_page,
        'query': query
    })


@user_passes_test(lambda user: user.groups.filter(name__in=["sales_manager", "operations_manager"]).exists())
def lead_history_view(request, lead_id):
    lead_history = None
    page_number = request.GET.get('page', 1)  # Get the page number from the request

    # Get the specific lead by ID
    lead = Lead.objects.get(id=lead_id)

    # Retrieve the lead's termination history
    lead_history = LeadTerminationHistory.objects.filter(lead=lead).order_by("-entry_date")
    
    # Paginate the lead history
    paginator = Paginator(lead_history, 10)  # Show 10 history records per page
    try:
        lead_history = paginator.page(page_number)
    except PageNotAnInteger:
        lead_history = paginator.page(1)
    except EmptyPage:
        lead_history = paginator.page(paginator.num_pages)

    context = {
        'lead': lead,
        'lead_history': lead_history,
    }
    
    return render(request, 'sales_manager/lead_history.html', context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales_team_leader", "sales_manager"]).exists())
@login_required
def search(request):
    user = request.user
    # Dynamically determine the template path based on user group
    if user.groups.filter(name="sales_manager").exists():
        template_path = "sales_manager/search.html"
    elif user.groups.filter(name="sales_team_leader").exists():
        template_path = "sales_team_leader/search.html"
    else:
        # Fallback for users with no recognized group
        template_path = "sales_manager/search.html"

    # --- Get query and search type ---
    query = request.GET.get('query', '').strip() if request.method == 'GET' else request.POST.get('query', '').strip()
    search_by = request.GET.get('search_by', '') if request.method == 'GET' else request.POST.get('search_by', '')

    leads_with_shows = []
    shows_queryset = None

    # --- Case 1: Search by show name (only shows, no leads) ---
    if search_by == 'show_name' and query:
        shows_queryset = SalesShow.objects.filter(
            Agent__isnull=False,
            name__icontains=query
        ).select_related('Agent').distinct()

        paginator = Paginator(shows_queryset, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'shows_only': True,
            'shows': page_obj,
            'query': query,
            'search_by': search_by,
        }
        return render(request, template_path, context)

    # --- Case 2: Lead-based search (lead_name or phone_number) ---
    leads_queryset = Lead.objects.filter(sales_shows__Agent__isnull=False)

    if query and search_by:
        leads_queryset = Lead.objects.filter(sales_shows_Agent_isnull=False)
        if search_by == 'lead_name':
            leads_queryset = leads_queryset.filter(name__icontains=query)

            leads_queryset = leads_queryset.prefetch_related(
                Prefetch(
                    'sales_shows',
                    queryset=SalesShow.objects.filter(Agent__isnull=False).select_related('Agent'),
                    to_attr='filtered_sales_shows'
                )
            ).distinct()

            for lead in leads_queryset:
                for show in lead.filtered_sales_shows:
                    leads_with_shows.append((lead, show))

        elif search_by == 'phone_number':
            phone_entries = LeadPhoneNumbers.objects.filter(value__icontains=query).values('lead_id', 'sheet_id')
            lead_ids = [entry['lead_id'] for entry in phone_entries]
            sheet_ids = [entry['sheet_id'] for entry in phone_entries]

            leads_queryset = leads_queryset.filter(id__in=lead_ids)

            leads_queryset = leads_queryset.prefetch_related(
                Prefetch(
                    'sales_shows',
                    queryset=SalesShow.objects.filter(Agent__isnull=False).select_related('Agent'),
                    to_attr='all_sales_shows'
                )
            ).distinct()

            for lead in leads_queryset:
                matching_shows = [
                    show for show in lead.all_sales_shows
                    if show.sheet_id in sheet_ids and lead.id in show.leads.values_list('id', flat=True)
                ]
                if matching_shows:
                    for show in matching_shows:
                        leads_with_shows.append((lead, show))
                else:
                    leads_with_shows.append((lead, None))
        else:
            leads_queryset = leads_queryset.prefetch_related(
                Prefetch(
                    'sales_shows',
                    queryset=SalesShow.objects.filter(Agent__isnull=False).select_related('Agent'),
                    to_attr='filtered_sales_shows'
                )
            ).distinct()

            for lead in leads_queryset:
                for show in lead.filtered_sales_shows:
                    leads_with_shows.append((lead, show))
    else:
        leads_queryset = leads_queryset.prefetch_related(
            Prefetch(
                'sales_shows',
                queryset=SalesShow.objects.filter(Agent__isnull=False).select_related('Agent'),
                to_attr='filtered_sales_shows'
            )
        ).distinct()

        for lead in leads_queryset:
            for show in lead.filtered_sales_shows:
                leads_with_shows.append((lead, show))

    # --- Pagination ---
    paginator = Paginator(leads_with_shows, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'shows_only': False,
        'leads_with_shows': page_obj,
        'query': query,
        'search_by': search_by,
    }

    return render(request, template_path, context)


@user_passes_test(lambda user: is_in_group(user, 'sales_manager'))
def sales_manager_notifications(request):
    user = request.user
    notifications_for_user = Notification.objects.filter(
        receiver=user).order_by('-created_at')

    # Implement pagination (e.g., 50 notifications per page)
    page = request.GET.get('page', '')
    paginator = Paginator(notifications_for_user, 10)

    try:
        notifications_page = paginator.page(page)
    except PageNotAnInteger:
        notifications_page = paginator.page(1)
    except EmptyPage:
        notifications_page = paginator.page(paginator.num_pages)

    return render(request, 'sales_manager/notifications.html', {
        'notifications': notifications_page
    })
