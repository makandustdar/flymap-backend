from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("sites", views.sites_collection, name="sites_collection"),
    path(
        "sites/<slug:site_id>/forecast",
        views.site_forecast,
        name="site_forecast",
    ),
    path("sites/<slug:site_id>", views.site_detail, name="site_detail"),
    path("ingest/windy", views.ingest_windy, name="ingest_windy"),
]
