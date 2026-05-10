from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="admin:index", permanent=False), name="root"),
    path("admin/", admin.site.urls),
    path("core/", include("core.urls")),
]
if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
