from django.urls import path, re_path
from .views import (agent_assigned_shows, index, show_detail, view_done_recycled_shows, sales_notifications,
                    view_done_shows, view_recycled_shows, view_saved_leads) # search is not needed at the moment
from main.views import mark_as_read

app_name = "sales"


urlpatterns = [
    path('', index, name="index"),
    path('assigned-shows/', agent_assigned_shows, name='assigned-shows'),
    path('done-shows/', view_done_shows, name='view-done-shows'),
    re_path(r'^view-saved-leads/(?P<code_id>\d+)?/?$',
            view_saved_leads, name='view_saved_leads'),
    re_path(r'^view-saved-leads/(?P<code_id>\d+)?/?$',
            view_saved_leads, name='view-saved-leads'),
    path('show-detail/<int:show_id>/', show_detail, name='show-detail'),
    path('show-detail/<int:show_id>/<str:recycle>/',
         show_detail, name='show-detail-recycle'),
    path("view-recycled-shows/", view_recycled_shows, name="view-recycled-shows"),
    path("view-done-recycled-shows/", view_done_recycled_shows,
         name="view-done-recycled-shows"),
#     path("search/", search, name="search")
     path('notifications/', sales_notifications, name='notifications'),
     path('notifications/<int:notification_id>/mark-as-read/', mark_as_read, name='mark_as_read'),
]
