from django.contrib import admin
from django.urls import path, include
from rag.views import health_check

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("api/", include("rag.urls")),
]