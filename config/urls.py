from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "SMP Dashboard admin"
admin.site.site_title = "SMP Dashboard"
admin.site.index_title = "Manage products, categories and data sources"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("products/", include("apps.catalog.urls")),
    path("trending/", include("apps.research.urls")),
    path("calculator/", include("apps.finance.urls")),
    path("", include("apps.watchlist.urls")),
    path("", include("apps.dashboard.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
