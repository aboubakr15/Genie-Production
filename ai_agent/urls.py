from django.urls import path
from .views import (
    data_enrichment_view,
    index,
    enrichment_results_page,
    get_enrichment_status,
    download_enrichment_file,
    task_dashboard_view,
    category_list_view,
    category_add_view,
    category_edit_view,
    category_delete_view,
)
from .utils import get_enrichment_progress

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
    # Category management URLs
    path('categories/', category_list_view, name='category_list'),
    path('categories/add/', category_add_view, name='category_add'),
    path('categories/edit/<int:category_id>/', category_edit_view, name='category_edit'),
    path('categories/delete/<int:category_id>/', category_delete_view, name='category_delete'),
]
