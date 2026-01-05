from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import User
from main.custom_decorators import is_in_group
from main.models import (LeadContactNames, LeadEmails, LeadPhoneNumbers, LeadTerminationCode, IncomingsCount,
                        LeadTerminationHistory, SalesShow, SalesTeams, TerminationCode, UserLeader, Lead, Notification,
                        FlagsCount)
from django.db.models import Count, Sum
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseBadRequest
from django.utils import timezone
from datetime import datetime
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage


@user_passes_test(lambda user: is_in_group(user, "sales_team_leader"))
def index(request):
    user = request.user  # Get the currently logged-in user

    # Get user IDs of team members
    team_members = UserLeader.objects.filter(leader=user).values_list('user', flat=True)

    # Convert to a list for manipulation
    team_members = list(team_members)

    # Add the user to the list if not already included
    if user.id not in team_members:
        team_members.append(user.id)


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
        user__in=team_members, 
        flag__name__in=['PR', 'CB']
    ).filter(entry_date__range=(start_date, end_date)).count()

    # Incomings
    '''''
    This model is used to count the incomings that have been made since the start of operating on the App,
    so it does not change at the dashboard if the termination code was changed.
    ''''' 
    incomings = IncomingsCount.objects.filter(user__in=team_members).filter(date__range=(start_date, end_date)).count()

    # Flags (Qualified and Non-Qualified)
    flags_qualified = FlagsCount.objects.filter(
        user__in=team_members, is_qualified=True
    ).filter(date__range=(start_date, end_date)).count()

    flags_non_qualified = FlagsCount.objects.filter(
        user__in=team_members, is_qualified=False
    ).filter(date__range=(start_date, end_date)).count()

    total_flags = flags_qualified + flags_non_qualified

    # Avg. #Calls
    avg_calls = SalesShow.objects.filter(
        Agent__in=team_members, 
        is_done=True
    ).filter(done_date__range=(start_date, end_date)).aggregate(total_leads=Count('leads'))['total_leads'] or 0

    # CD Count
    cd_count = LeadTerminationCode.objects.filter(
        user__in=team_members, 
        flag__name='CD'
    ).filter(entry_date__range=(start_date, end_date)).count()

    # Total #Nights
    total_nights = LeadTerminationCode.objects.filter(
        user__in=team_members, 
        flag__name='CD'
    ).filter(entry_date__range=(start_date, end_date)).aggregate(total_nights=Sum('num_nights'))['total_nights'] or 0

    return render(request, "sales_team_leader/index.html", {
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


@user_passes_test(lambda user: user.groups.filter(name__in=["sales_team_leader", "sales_manager"]).exists())
def view_team_shows(request, leader_id=None):
    leader = None 
    if leader_id:
        leader=User.objects.get(id=leader_id)
    else:
        leader=request.user

    team_members = list(UserLeader.objects.filter(leader=leader).values("user__id", "user__username"))

    if leader_id is not None:
        team_members.append({
            'user__id': leader.id,
            'user__username': leader.username
        })

    team_name = SalesTeams.objects.get(leader=leader).label

    context = {
        'team_name':team_name,
        'team_members':team_members,
        'role':request.user.groups.first().name
    }

    return render(request, "sales_team_leader/view_team_shows.html", context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales_team_leader", "sales_manager"]).exists())
def view_team_member(request, member_id, label="new"):
    # Fetch the SalesShow instances for the specified team member
    shows = SalesShow.objects.filter(Agent__id=member_id, is_done=(label=="done")).order_by('-id')

    # Get the team member object (optional)
    member = get_object_or_404(User, id=member_id)

    context = {
        'member': member,
        'shows': shows,
        'label':label
    }

    return render(request, "sales_team_leader/view_team_member.html", context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales_team_leader", "sales_manager"]).exists())
def view_team_prospect(request, code_id=None, leader_id=None):
    code = get_object_or_404(TerminationCode, name='CB') if code_id is None else get_object_or_404(TerminationCode, id=code_id)

    role = request.user.groups.first().name if request.user.groups.exists() else None

    my_allowed = ['CB', 'PR', 'CD', 'FL', 'IC', 'ST']

    if code.name not in my_allowed:
        return HttpResponseBadRequest()
    
    
    if leader_id:
        leader=User.objects.get(id=leader_id)
    elif role=="sales_team_leader":
        leader = request.user
    else:
        return HttpResponseBadRequest()

    termination_codes = TerminationCode.objects.filter(name__in=my_allowed)
    termination_codes_selection = TerminationCode.objects.all()

    team_members = list(UserLeader.objects.filter(leader=leader).values_list('user', flat=True))
    if leader_id is not None:
        team_members.append(
            leader.id
        )

    order_by = request.GET.get('order_by', '-entry_date')  # Default sorting

    if code.name == 'ST':
        leads = LeadTerminationCode.objects.filter(target_user=request.user, flag=code).order_by(order_by)
    else:
        leads = LeadTerminationCode.objects.filter(user__in=team_members, flag=code).order_by(order_by)
    team_name = SalesTeams.objects.filter(leader=leader).first().label

    # Search Logic
    search_query = request.GET.get('search_query', '')
    if search_query:
        from django.db.models import Q
        leads = leads.filter(
            Q(lead__name__icontains=search_query) | 
            Q(lead__leadphonenumbers__value__icontains=search_query)
        ).distinct()
    
    # Fetch potential target users (Team Leaders and Sales Managers)
    target_users = User.objects.filter(groups__name__in=['sales_team_leader', 'sales_manager']).distinct()


    if request.method == 'POST':
        for lead_termination in leads:
            lead_id = lead_termination.lead.id
            sales_show_id = lead_termination.sales_show.id
            status = request.POST.get(f'status_{lead_id}_{sales_show_id}')
            num_rooms = request.POST.get(f'rooms_{lead_id}_{sales_show_id}')
            num_nights = request.POST.get(f'nights_{lead_id}_{sales_show_id}')
            notes = request.POST.get(f'notes_{lead_id}_{sales_show_id}')
            options = request.POST.get(f'options_{lead_id}_{sales_show_id}')
            termination_code_id = request.POST.get(f'termination_code_{lead_id}_{sales_show_id}')
            cb_date = request.POST.get(f'cb_date_{lead_id}_{sales_show_id}')
            is_qualified = request.POST.get(f'is_qualified_{lead_id}') == 'on'  # Check if the checkbox is checked

            target_user_id = request.POST.get(f'target_user_{lead_id}_{sales_show_id}')
            target_user = None
            if target_user_id:
                target_user = User.objects.get(id=target_user_id)

            if isinstance(cb_date, str):
                cb_date = cb_date.strip() if cb_date.strip() else None

            new_code = TerminationCode.objects.get(id=termination_code_id)

            if status:
                lead_termination.status = status
            if num_rooms:
                lead_termination.num_rooms = int(num_rooms)
            if num_nights:
                lead_termination.num_nights = int(num_nights)
            if options:
                lead_termination.options = options.strip()
            if new_code:
                lead_termination.flag = new_code
            if cb_date:
                lead_termination.CB_date = cb_date
            if notes:
                lead_termination.notes = notes
            
            lead_termination.target_user = target_user

            latest_termination = LeadTerminationHistory.objects.filter(lead=lead_termination.lead).order_by('-entry_date').first()

            # Only create a new entry if there's a new termination code or callback date
            if latest_termination is None or (
                (new_code is not None and latest_termination.termination_code != new_code) or
                (cb_date is not None and latest_termination.cb_date != cb_date)
                ):
                # Create a new history record if either field has changed
                LeadTerminationHistory.objects.create(
                    user=request.user,
                    termination_code=new_code,
                    cb_date=cb_date,
                    lead=lead_termination.lead,
                    show=lead_termination.sales_show,
                    notes=notes,
                    target_user=target_user
                )


            # Only for flag termination code
            lead_termination.is_qualified = is_qualified  # Set the checkbox value
            lead_termination.save()

        if role=="sales_team_leader":
            return redirect('sales_team_leader:view-team-prospect-with-id', code_id=code.id)
        else:
            return redirect('sales_manager:view-team-prospect-with-leader', code_id=code.id, leader_id=leader_id)
        
    paginator = Paginator(leads, 20)  # Show 20 leads per page
    page = request.GET.get('page')
    try:
        leads_page = paginator.page(page)
    except PageNotAnInteger:
        leads_page = paginator.page(1)
    except EmptyPage:
        leads_page = paginator.page(paginator.num_pages)
    
    # leads_data = []

    lead_ids = [l.lead.id for l in leads_page]
    show_ids = [l.sales_show.id for l in leads_page]
    sheet_ids = [l.sales_show.sheet.id for l in leads_page]

    # Bulk fetch phones, emails, and contacts
    all_phones = {p.lead_id: [] for p in LeadPhoneNumbers.objects.filter(lead_id__in=lead_ids, sheet_id__in=sheet_ids)}
    for p in LeadPhoneNumbers.objects.filter(lead_id__in=lead_ids, sheet_id__in=sheet_ids):
        all_phones[p.lead_id].append(p)
    
    all_emails = {e.lead_id: [] for e in LeadEmails.objects.filter(lead_id__in=lead_ids, sheet_id__in=sheet_ids)}
    for e in LeadEmails.objects.filter(lead_id__in=lead_ids, sheet_id__in=sheet_ids):
        all_emails[e.lead_id].append(e.value)
    
    all_contacts = {c.lead_id: [] for c in LeadContactNames.objects.filter(lead_id__in=lead_ids, sheet_id__in=sheet_ids)}
    for c in LeadContactNames.objects.filter(lead_id__in=lead_ids, sheet_id__in=sheet_ids):
        all_contacts[c.lead_id].append(c.value)
    
    # Bulk fetch previous CB dates
    all_cb_dates = {}
    for hist in LeadTerminationHistory.objects.filter(lead_id__in=lead_ids, show_id__in=show_ids).exclude(cb_date__isnull=True).select_related('lead', 'show'):
        key = (hist.lead_id, hist.show_id)
        if key not in all_cb_dates:
            all_cb_dates[key] = []
        all_cb_dates[key].append(hist.cb_date)

    leads_data = []
    for lead_termination in leads_page:
        lead = lead_termination.lead
        sales_show = lead_termination.sales_show

        # Use prefetched data
        phones = all_phones.get(lead.id, [])
        emails = all_emails.get(lead.id, [])
        contacts = all_contacts.get(lead.id, [])
        
        # Get previous CB dates from prefetched data
        previous_cb_dates = sorted(set(all_cb_dates.get((lead.id, sales_show.id), [])))

        previous_cb_dates = sorted(previous_cb_dates)

        leads_data.append({
            'lead': lead,
            'sender': lead_termination.user,  # Sender of the lead
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
            # 'timezone': lead.time_zone,
            'Agent': sales_show.Agent,
            'termination_code_id': lead_termination.flag.id,
            'is_qualified': lead_termination.is_qualified,
            'sales_show_id': sales_show.id,
            'sales_show': sales_show,
            'entry_date': lead_termination.entry_date,
            'target_user': lead_termination.target_user,
        })

    context = {
        'leads_data': leads_data,
        'leads_page': leads_page,
        'termination_codes': termination_codes,
        'termination_codes_selection':termination_codes_selection,
        'selected_code': code,
        'cb_code_id':TerminationCode.objects.get(name="CB").id,
        'role':role,
        'team_name':team_name,
        'leader':leader,
        'search_query': search_query,
        'target_users': target_users,
    }

    if code.name in ['CB', 'IC']:
        return render(request, "sales_team_leader/view_team_prospect.html", context)
    elif code.name in ['FL', 'PR', 'CD']:
        return render(request, "sales_team_leader/view_team_prospect_FL_PR.html", context)
    elif code.name == 'ST':
        return render(request, "sales_team_leader/view_team_prospect_ST.html", context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales_team_leader", "sales_manager"]).exists())
def view_team_recycled(request, leader_id=None):
    leader = None 
    role=request.user.groups.first().name
    if leader_id:
        leader=User.objects.get(id=leader_id)
    elif role=="sales_team_leader":
        leader=request.user
    else:
        return HttpResponseBadRequest()

    team_members = UserLeader.objects.filter(leader=leader).values("user__id", "user__username")
    team_name = SalesTeams.objects.get(leader=leader).label

    context = {
        'team_name':team_name,
        'team_members':team_members,
        'role':role
    }

    return render(request, "sales_team_leader/view_team_recycled.html", context)


@user_passes_test(lambda user: user.groups.filter(name__in=["sales_team_leader", "sales_manager"]).exists())
def view_team_member_recycled(request, member_id, label="new"):
    member = get_object_or_404(User, id=member_id)
    role=request.user.groups.first().name
    
    # Filter shows based on the label
    if label == "done":
        shows = SalesShow.objects.filter(Agent=member, is_recycled=True, is_done_rec=True).order_by("-id")
    else:  # default to "new"
        shows = SalesShow.objects.filter(Agent=member, is_recycled=True, is_done_rec=False).order_by("-id")

    context = {
        'member': member,
        'shows': shows,
        'label': label,
        'role':role
    }

    return render(request, "sales_team_leader/view_team_member_recycled.html", context)


@user_passes_test(lambda user: is_in_group(user, "sales_team_leader"))
def sales_team_leader_notifications(request):
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

    return render(request, 'sales_team_leader/notifications.html', {
        'notifications': notifications_page
    })



## Used for search withtin the scope of the user's team but disabeled for now and using the sales_manager search instead
{
# @user_passes_test(lambda user: user.groups.filter(name__in=["sales_team_leader", "sales_manager"]).exists())
# def search(request):
#     if request.method == 'GET':
#         return render(request, "sales_team_leader/search.html")

#     leads_with_shows = []  # List to hold leads with their corresponding shows
#     query = request.POST.get('query', '').strip()
#     search_by = request.POST.get('search_by', 'lead_name')  # Default search by lead name

#     # Get the current user (sales team leader)
#     current_user = request.user

#     # Get shows for the current user
#     user_shows = SalesShow.objects.filter(Agent=current_user)

#     # Get leads from the user's shows
#     user_leads = Lead.objects.filter(sales_shows__in=user_shows).distinct().order_by('-id')

#     # Get team members of the current user
#     team_members = UserLeader.objects.filter(leader=current_user).values_list('user', flat=True)

#     # Get shows for the team members
#     team_member_shows = SalesShow.objects.filter(Agent__in=team_members).order_by('-id')

#     # Get leads from the team members' shows
#     team_member_leads = Lead.objects.filter(sales_shows__in=team_member_shows).distinct().order_by('-id')

#     # Combine user and team member leads
#     all_leads = user_leads | team_member_leads

#     # If there is a search query, filter based on the selected search_by option
#     if query:
#         if search_by == 'lead_name':
#             all_leads = all_leads.filter(name__icontains=query).distinct()
#         elif search_by == 'phone_number':
#             phone_numbers = LeadPhoneNumbers.objects.filter(
#                 value__icontains=query,
#                 sheet__in=user_shows.values('sheet') | team_member_shows.values('sheet')
#             )
#             all_leads = Lead.objects.filter(id__in=phone_numbers.values('lead_id')).distinct()
#         elif search_by == 'show_name':
#             shows_by_name = SalesShow.objects.filter(name__icontains=query, Agent__in=[current_user] + list(team_members))
#             all_leads = Lead.objects.filter(sales_shows__in=shows_by_name).distinct()

#     # Create a list of tuples (lead, show) for each lead's associated shows
#     for lead in all_leads:
#         shows = lead.sales_shows.filter(Agent__in=[current_user] + list(team_members))
#         for show in shows:
#             leads_with_shows.append((lead, show))

#     # Paginate results
#     paginator = Paginator(leads_with_shows, 10)  # Show 10 leads per page
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     context = {
#         'leads_with_shows': page_obj,
#         'query': query,
#         'search_by': search_by,
#     }

#     return render(request, "sales_team_leader/search.html", context)
}