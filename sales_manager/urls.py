from django.urls import path, re_path
from sales_team_leader.views import (view_team_member, view_team_member_recycled,
    view_team_prospect, view_team_recycled, view_team_shows)
from .views import (assign_sales_to_leader, index, manage_sales_teams, view_teams_prospect, sales_manager_notifications,
    view_teams_shows, view_teams_shows_recycled, lead_history_view, leads_inventory, search)
from sales.views import (agent_assigned_shows, show_detail, view_done_recycled_shows,
    view_done_shows, view_recycled_shows, view_saved_leads)
from main.views import lead_details, sales_log_view, mark_as_read
from operations_manager.views import manage_referrals


app_name="sales_manager"

urlpatterns = [
    path("", index, name="index"),
    path('assign-sales-to-leader', assign_sales_to_leader,
         name='assign-sales-to-leader'),
    path('manage-sales-teams', manage_sales_teams, name='manage-sales-teams'),
    path('assigned-shows/', agent_assigned_shows, name='assigned-shows'),
    path('done-shows/', view_done_shows, name='view-done-shows'),
    path('show-detail/<int:show_id>/', show_detail, name='show-detail'),
    path('view-teams-prospect/', view_teams_prospect, name='view-teams-prospect'),
    path("view-team-prospect/<int:code_id>/<int:leader_id>",
         view_team_prospect, name='view-team-prospect-with-leader'),
    path("view-teams-shows", view_teams_shows, name="view-teams-shows"),
    path("view-team-shows/<int:leader_id>", view_team_shows,
         name='view-team-shows-with-leader'),
    path("view-team-member-shows/<int:member_id>/<str:label>",
         view_team_member, name='view-team-member-shows'),
    re_path(r'^view-saved-leads/(?P<code_id>\d+)?/?$',
            view_saved_leads, name='view-saved-leads'),
    path("view-recycled-shows", view_recycled_shows, name="view-recycled-shows"),
    path("view-done-recycled-shows", view_done_recycled_shows,
         name="view-done-recycled-shows"),
    path("view-teams-recycled", view_teams_shows_recycled,
         name="view-teams-shows-recycled"),
    path("view-team-recycled/<int:leader_id>",
         view_team_recycled, name="view-team-recycled"),
    path("view-team-member-recycled/<int:member_id>/<str:label>",
         view_team_member_recycled, name="view-team-member-recycled"),
    path('leads-inventory/', leads_inventory, name='leads-inventory'),
    path('lead-details/<int:pk>/', lead_details, name='lead-details'),
    path('lead-history/<int:lead_id>/', lead_history_view, name='lead-history'),
    path('search/', search, name='search'),
    path('sales-log/', sales_log_view, name='sales-logs'),
    path('manage-referrals/', manage_referrals, name='manage-referrals'),
    path('notifications/', sales_manager_notifications, name='notifications'),
    path('notifications/<int:notification_id>/mark-as-read/', mark_as_read, name='mark_as_read'),
]