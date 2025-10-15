from django.urls import path
from .views import data_enrichment_view, index, get_enrichment_progress, download_enrichment_results, get_enrichment_status

app_name = 'ai_agent'

urlpatterns = [
    path('', index, name="index"),
    path('search/', index, name="search"),
    path('enrich_data/', data_enrichment_view, name="data_enrichment"),
    path('enrichment_progress/', get_enrichment_progress, name='enrichment_progress'),
    path('download_results/<str:task_id>/', download_enrichment_results, name='download_enrichment_results'),
    path('enrichment_status/<str:task_id>/', get_enrichment_status, name='enrichment_status'),
]
