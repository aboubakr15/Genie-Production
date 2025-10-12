from django.urls import path
from .views import data_enrichment_view, index, get_enrichment_progress, download_excel

app_name = 'ai_agent'

urlpatterns = [
    path('', index, name="index"),
    path('search/', index, name="search"),
    path('enrich_data/', data_enrichment_view, name="enrich"),
    path('enrichment_progress/', get_enrichment_progress, name='enrichment_progress'),
    path('download/<str:filename>/', download_excel, name='download_excel'),
]
