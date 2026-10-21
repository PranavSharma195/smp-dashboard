from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.calculator, name="calculator"),
    path("api/", views.calculate_api, name="api"),
]
