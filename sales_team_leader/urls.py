from django.urls import path, re_path
from .views import (view_team_member_recycled, index, view_team_member, view_team_prospect, view_team_recycled,
                    view_team_shows, sales_team_leader_notifications)
from sales.views import (agent_assigned_shows, show_detail, view_done_recycled_shows,
    view_done_shows, view_recycled_shows, view_saved_leads)
from main.views import sales_log_view, mark_as_read
from sales_manager.views import search

app_name="sales_team_leader"

urlpatterns = [
    path('', index, name='index'),
    path("assigned-shows", agent_assigned_shows, name='assigned-shows'),
    path("show-detail/<int:show_id>/", show_detail, name='show-detail'),
    path('show-detail/<int:show_id>/<str:recycle>/',
         show_detail, name='show-detail-recycle'),
    path("view-done-shows/", view_done_shows, name='view-done-shows'),
    path("view-saved-leads/", view_saved_leads, name='view-saved-leads'),
    path("view-team-shows/", view_team_shows, name='view-team-shows'),
    path("view-team-member-shows/<int:member_id>/<str:label>/",
         view_team_member, name='view-team-member-shows'),
    path("view-team-prospect/", view_team_prospect, name='view-team-prospect'),
    path("view-team-prospect/<int:code_id>/",
         view_team_prospect, name='view-team-prospect-with-id'),
    re_path(r'^view-saved-leads/(?P<code_id>\d+)?/?$',
            view_saved_leads, name='view-saved-leads'),
    path("view-recycled-shows/", view_recycled_shows, name="view-recycled-shows"),
    path("view-done-recycled-shows/", view_done_recycled_shows,
         name="view-done-recycled-shows"),
    path("view-team-recycled/", view_team_recycled, name="view-team-recycled"),
    path("view-team-member-recycled/<int:member_id>/<str:label>/",
         view_team_member_recycled, name="view-team-member-recycled"),
    path("search", search, name='search'),
    path('sales-log/', sales_log_view, name='sales-logs'),
    path('notifications/', sales_team_leader_notifications, name='notifications'),
    path('notifications/<int:notification_id>/mark-as-read/', mark_as_read, name='mark_as_read'),
]