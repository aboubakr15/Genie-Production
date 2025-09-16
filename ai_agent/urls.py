from django.urls import path
from .views import data_enrichment_view, index

app_name = 'ai_agent'

urlpatterns = [
    path('', index, name="index"),
    path('search/', index, name="search"),
    path('enrich_data/', data_enrichment_view, name="enrich"),
]
