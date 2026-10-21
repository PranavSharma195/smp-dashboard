from django.urls import path

from . import views

app_name = "research"

urlpatterns = [
    path("", views.trending, name="trending"),
    path("methodology/", views.methodology, name="methodology"),
]
