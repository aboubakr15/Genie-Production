from django.urls import path

from .views import index, login_view, logout_view, sheet_list, log_inactivity

app_name="main"

urlpatterns = [
    path("", index, name="index"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path('api/sheets/', sheet_list, name='sheet-list'),
    path('log-inactivity/', log_inactivity, name='log_inactivity'),
]