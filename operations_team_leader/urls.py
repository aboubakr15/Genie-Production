from django.urls import path, re_path
from .views import accept_auto_fill_notification, index, notifications, notification_detail, accept_upload_notification
from .views import decline_upload_notification, view_sheet, delete_excel_lead, edit_excel_lead
from main.views import (lead_details, auto_fill, edit_lead, delete_lead, upload_sheet, add_lead,
                        leads_average_view, manage_filter_words, delete_filter_word, import_folder)

app_name="operations_team_leader"

urlpatterns = [
    path('', index, name="index"),
    path('add-lead/', add_lead, name='add-lead'),
    path('upload-sheet/', upload_sheet, name='upload-sheet'),
    path('leads-average/', leads_average_view, name='leads-average'),
    path('lead-details/<int:pk>/', lead_details, name='lead-details'),
    path('notifications/', notifications, name='notifications'),
    path('auto-fill/', auto_fill, name='auto-fill'),
    path('edit-lead/<int:pk>/', edit_lead, name='edit-lead'),
    path('delete-lead/<int:pk>/', delete_lead, name='delete-lead'),
    path('notifications/<int:notification_id>/', notification_detail, name='notification-detail'),
    path('notifications/<int:notification_id>/accept-upload/', accept_upload_notification, name='accept-upload-notification'),
    path('notifications/<int:notification_id>/decline-upload/', decline_upload_notification, name='decline-upload-notification'),
    path('notifications/<int:notification_id>/accept-auto-fill-notification/', accept_auto_fill_notification, name='accept-auto-fill-notification'),
    path('notifications/<int:notification_id>/sheet/<int:sheet_id>/', view_sheet, name='view-sheet'),
    # path('notifications/<int:notification_id>/sheet/<int:sheet_id>/delete/<str:company_name>/', delete_excel_lead, name='delete-excel-lead'),
    # path('notifications/<int:notification_id>/sheet/<int:sheet_id>/edit/<str:company_name>/', edit_excel_lead, name='edit-excel-lead'),
    re_path(r'^notifications/(?P<notification_id>\d+)/sheet/(?P<sheet_id>\d+)/delete/(?P<company_name>.+)/$', delete_excel_lead, name='delete-excel-lead'),
    re_path(r'^notifications/(?P<notification_id>\d+)/sheet/(?P<sheet_id>\d+)/edit/(?P<company_name>.+)/$', edit_excel_lead, name='edit-excel-lead'),
    path('manage-filter-words/', manage_filter_words, name='manage-filter-words'),
    path('delete-filter-word/<int:word_id>/', delete_filter_word, name='delete-filter-word'),
    path('upload-X/', import_folder, name='upload-x'),
]

