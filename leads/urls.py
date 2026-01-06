from django.urls import path
from .views import index, auto_fill, notifications, notification_detail, sheet_detail, upload_sheet, download_auto_fill_result
from main.views import leads_average_view
from django.conf import settings
from django.conf.urls.static import static

app_name="leads"

urlpatterns = [
    path('', index, name='leads_index'),
    path('auto-fill/', auto_fill, name='auto-fill'),
    path('upload-sheet/', upload_sheet, name='upload-sheet'),
    path('leads-average/', leads_average_view, name='leads-average'),
    # path('import-sheets/', import_lead_termination_history, name='import-sheets'),
    path('notifications/', notifications, name='notifications'),
    path('notifications/<int:notification_id>/', notification_detail, name='leads-notification-detail'),
    path('notifications/<int:notification_id>/sheet/<int:sheet_id>/', sheet_detail, name='leads-sheet-detail'),
    path('notifications/<int:notification_id>/download-auto-fill-result/', download_auto_fill_result, name='download-auto-fill-result'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)