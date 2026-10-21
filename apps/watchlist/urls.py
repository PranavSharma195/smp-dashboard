from django.urls import path

from . import views

app_name = "watchlist"

urlpatterns = [
    path("watchlist/", views.watchlist_page, name="list"),
    path("watchlist/toggle/<int:pk>/", views.watch_toggle, name="toggle"),
    path("compare/", views.compare_page, name="compare"),
    path("compare/toggle/<int:pk>/", views.compare_toggle, name="compare_toggle"),
    path("compare/clear/", views.compare_clear, name="compare_clear"),
]
