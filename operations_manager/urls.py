from django.urls import path
from .views import (assign_lead_to_leader, done_ready_shows, index, manage_leads_teams,
    sheet_detail, unassigned_sales_shows, view_agent_done_shows, view_sales_agents)

from .views import (assign_sales_show, ready_shows_view, cut_ready_show_into_sales_shows, price_requests_view,view_ready_show,
                    cut_ready_shows, archived_sales_shows, assigned_sales_shows, update_price_requests,
                    manage_referrals, notifications, archive_sales_show, unarchive_sales_show, archive_ready_show, 
                    reassign_sales_show, unarchive_ready_show, archived_ready_shows, unassigned_x_sales_shows,
                    archive_ready_show_bulk, reassigned_sales_shows, archive_sales_show_bulk)

from main.views import (lead_details, auto_fill, edit_lead, delete_lead, add_lead, import_folder,
                        upload_sheet, manage_filter_words, delete_filter_word)

from sales_manager.views import lead_history_view
from operations_team_leader.views import view_sheet
from sales.views import show_detail


app_name="operations_manager"

urlpatterns = [
    path('', index, name="index"),
    path('manage-leads-teams/', manage_leads_teams, name='manage-leads-teams'),
    path('lead-details/<int:pk>/', lead_details, name='lead-details'),
    path('assign-lead-to-leader/', assign_lead_to_leader, name='assign-lead-to-leader'),
    path('upload-sheet/', upload_sheet, name='upload-sheet'),
    path('auto-fill/', auto_fill, name='auto-fill'),
    path('sheet/<int:sheet_id>/', sheet_detail, name='sheet-detail'),
    path('edit-lead/<int:pk>/', edit_lead, name='edit-lead'),
    path('add-lead/', add_lead, name='add-lead'),
    path('delete-lead/<int:pk>/', delete_lead, name='delete-lead'),
    path('ready-shows/', ready_shows_view, name='ready-shows'),      # Default before choosing a tab
    path('ready-shows/<str:label>/', ready_shows_view, name='ready-shows'),
    path('cut-ready-show/<int:ready_show_id>/', cut_ready_show_into_sales_shows, name='cut-ready-show'),
    
    path('price-requests/', price_requests_view, name='price-requests'),

    path('update-price-requests/', update_price_requests, name='update_price_requests'),

    path('assign-sales-show/', assign_sales_show, name='assign_sales_show'),

    path('done-ready-shows/', done_ready_shows, name='done-ready-shows'),
    path('done-ready-shows/<str:label>/', done_ready_shows, name='done-ready-shows'),

    path('sales-shows/unassigned/', unassigned_sales_shows, name='unassigned-sales-shows'),
    path('sales-shows/unassigned/<str:label>/', unassigned_sales_shows, name='unassigned-sales-shows'),

    path('sales-shows/unassigned-x/', unassigned_x_sales_shows, name='unassigned-x-sales-shows'),
    
    path('sales-shows/assigned/', assigned_sales_shows, name='assigned-sales-shows'),
    path('sales-shows/assigned/<str:label>/', assigned_sales_shows, name='assigned-sales-shows'),

    path("view-sales-agents", view_sales_agents, name="view-sales-agents"),
    path("view-agent-done-shows/<int:agent_id>", view_agent_done_shows, name="view-agent-done-shows"),

    path('lead-history/<int:lead_id>/', lead_history_view, name='lead-history'),

    path('manage-filter-words/', manage_filter_words, name='manage-filter-words'),
    path('delete-filter-word/<int:word_id>/', delete_filter_word, name='delete-filter-word'),

    path('manage-referrals/', manage_referrals, name='manage-referrals'),

    path('show-detail/<int:show_id>/', show_detail, name='show-detail'),

    path('notifications/', notifications, name='notifications'),

    path('archive-sales-show/<int:show_id>/', archive_sales_show, name='archive-sales-show'),

    path('archive-sales-show-bulk/', archive_sales_show_bulk, name='archive_sales_show_bulk'),
    
    path('archive-ready-show-bulk/', archive_ready_show_bulk, name='archive_ready_show_bulk'),

    path('cut-ready-shows/', cut_ready_shows, name='cut-ready-shows'),

    path('unarchive/<int:show_id>/', unarchive_sales_show, name='unarchive-sales-show'),

    path('archived-sales-shows/', archived_sales_shows, name='archived-sales-shows'),

    path('archive-sheet/<int:show_id>/', archive_ready_show, name='archive-sheet'),
    path('archived-sheets/', archived_ready_shows, name='archived-sheets'),
    path('unarchive-sheet/<int:show_id>/', unarchive_ready_show, name='unarchive-sheet'),

    path('upload-X/', import_folder, name='upload-x'),

    path('ready-show/<int:show_id>/', view_ready_show, name='view-ready-show'),

    path('reassign-show/', reassign_sales_show, name='reassign-sales-show'),

    path('reassigned-unassigned-shows/', reassigned_sales_shows, name='reassigned-shows'),


]