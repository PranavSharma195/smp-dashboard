from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.explore, name="explore"),
    path("api/", views.api_products, name="api"),
    path("budget-finder/", views.budget_finder, name="budget_finder"),
    path("save-filters/", views.save_filters, name="save_filters"),
    path("clear-saved-filters/", views.clear_saved_filters, name="clear_saved_filters"),
    path("<slug:slug>/", views.product_detail, name="detail"),
]
