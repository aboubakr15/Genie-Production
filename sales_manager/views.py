from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import Group, User
from django.contrib import messages
from main.custom_decorators import is_in_group
from main.models import (LeadEmails, LeadContactNames, LeadPhoneNumbers, SalesTeams, TerminationCode, UserLeader,
                        LeadTerminationCode, SalesShow, LeadTerminationHistory, Lead, Notification, IncomingsCount)
from django.db.models import Count, Sum, OuterRef, Subquery, Prefetch
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.decorators import user_passes_test
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

    # Flags
    total_flags = LeadTerminationCode.objects.filter(
        flag__name='FL'
    ).filter(entry_date__range=(start_date, end_date)).count()

    flags_qualified = LeadTerminationCode.objects.filter(
        flag__name='FL',
        is_qualified=True
    ).filter(entry_date__range=(start_date, end_date)).count()

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
    recent_email = LeadEmails.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]
    recent_contact_name = LeadContactNames.objects.filter(lead=OuterRef('pk')).order_by('-id').values('value')[:1]

    if query:
        leads = Lead.objects.filter(name__icontains=query)
    else:
        leads = Lead.objects.all()
    
    # Annotate leads with recent contact information
    leads = leads.annotate(
        recent_phone_number=Subquery(recent_phone_number),
        recent_email=Subquery(recent_email),
        recent_contact_name=Subquery(recent_contact_name)
    )
    
    page = request.GET.get('page', '')
    paginator = Paginator(leads, 30)  

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
def search(request):
    # Handle GET for initial page load and pagination
    if request.method == 'GET':
        query = request.GET.get('query', '').strip()
        search_by = request.GET.get('search_by', '')
    else:  # POST for form submission
        query = request.POST.get('query', '').strip()
        search_by = request.POST.get('search_by', '')

    # Base queryset for leads with non-null Agent sales shows
    leads_queryset = Lead.objects.filter(sales_shows__Agent__isnull=False)

    # Apply search filters
    if query and search_by:
        if search_by == 'lead_name':
            leads_queryset = leads_queryset.filter(name__icontains=query)
        elif search_by == 'phone_number':
            phone_numbers = LeadPhoneNumbers.objects.filter(value__icontains=query).values('lead_id')
            leads_queryset = leads_queryset.filter(id__in=phone_numbers)
        elif search_by == 'show_name':
            leads_queryset = leads_queryset.filter(sales_shows__name__icontains=query)

    # Use Prefetch to eagerly load related sales shows with non-null Agent
    leads_queryset = leads_queryset.prefetch_related(
        Prefetch(
            'sales_shows',
            queryset=SalesShow.objects.filter(Agent__isnull=False).select_related('Agent'),
            to_attr='filtered_sales_shows'
        )
    ).distinct()

    # Create leads_with_shows list
    leads_with_shows = []
    for lead in leads_queryset:
        for show in lead.filtered_sales_shows:
            leads_with_shows.append((lead, show))

    # Paginate results
    paginator = Paginator(leads_with_shows, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'leads_with_shows': page_obj,
        'query': query,
        'search_by': search_by,
    }

    return render(request, "sales_manager/search.html", context)



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
