from django.urls import path
from .views import (
    data_enrichment_view,
    index,
    get_enrichment_progress,
    enrichment_results_page,
    get_enrichment_status,
    download_enrichment_file,
    task_dashboard_view,
)

app_name = 'ai_agent'

urlpatterns = [
    path('', index, name="index"),
    path('search/', index, name="search"),
    path('enrich_data/', data_enrichment_view, name="data_enrichment"),
    path('enrichment_progress/', get_enrichment_progress, name='enrichment_progress'),
    path('results/<str:task_id>/', enrichment_results_page, name='enrichment_results_page'),
    path('enrichment_status/<str:task_id>/', get_enrichment_status, name='enrichment_status'),
    path('files/download/<str:task_id>/', download_enrichment_file, name='download_file'),
    path('dashboard/', task_dashboard_view, name='task-dashboard'),
]
