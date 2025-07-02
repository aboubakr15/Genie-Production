"""
URL configuration for IBH project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include("main.urls")),
    path("administrator/", include("administrator.urls", namespace='administrator')),
    path("operations_team_leader/", include("operations_team_leader.urls", namespace='operations_team_leader')),
    path("sales_manager/", include("sales_manager.urls", namespace='sales_manager')),
    path("sales_team_leader/", include("sales_team_leader.urls", namespace='sales_team_leader')),
    path("operations_manager/", include("operations_manager.urls", namespace='operations_manager')),
    path("api/", include("api.urls", namespace='api')),
    path("leads/", include("leads.urls", namespace="leads")),
    path("sales/", include("sales.urls", namespace="sales")),
    path("admin/", admin.site.urls),
    path("ai_agent/", include("ai_agent.urls", namespace="ai_agent")),
]

if settings.DEBUG:
    # import debug_toolbar  # Import Debug Toolbar only in DEBUG mode
    # urlpatterns += [
    #     path("__debug__/", include(debug_toolbar.urls)),  # Add Debug Toolbar URLs
    # ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

