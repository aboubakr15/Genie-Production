from django.urls import path
from . import views

app_name = 'ai_agent'

urlpatterns = [
    path('', views.index, name="index"),
    path('search/', views.index, name="search"),
    path('enrich_data/', views.enrich_data, name="enrich"),
]
