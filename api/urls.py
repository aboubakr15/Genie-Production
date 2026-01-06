from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from .views import *

app_name="api"

urlpatterns = [
    path("add-phone-number", add_phone_number, name="add_phone_number"),
    path("add-email", add_email, name="add_email"),
    path("add-contact-name", add_contact_name, name="add_contact_name"),
]