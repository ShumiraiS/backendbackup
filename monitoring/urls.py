# monitoring/urls.py
from django.urls import path, include

from .auth_views import LoginAPIView
from .industries_views import IndustriesListAPIView
from .readings_views import LatestReadingByIndustryAPIView
from .stps_views import STPsListAPIView
from .stp_readings_views import LatestReadingBySTPAPIView
from .ai_views import AIAdviceAPIView
from .alerts_views import AlertsListAPIView, MarkAlertReadAPIView
from .map_views import MapOverviewAPIView
from .ingest_views import IngestIndustryReadingAPIView

urlpatterns = [
    # Main app endpoints
    path("login/", LoginAPIView.as_view(), name="login"),

    path("industries/", IndustriesListAPIView.as_view(), name="industries"),
    path("readings/latest/", LatestReadingByIndustryAPIView.as_view(), name="latest-reading-industry"),

    path("stps/", STPsListAPIView.as_view(), name="stps"),
    path("stp/readings/latest/", LatestReadingBySTPAPIView.as_view(), name="latest-reading-stp"),

    path("ai/advice/", AIAdviceAPIView.as_view(), name="ai-advice"),

    path("alerts/", AlertsListAPIView.as_view(), name="alerts-list"),
    path("alerts/mark-read/", MarkAlertReadAPIView.as_view(), name="alerts-mark-read"),

    path("map/overview/", MapOverviewAPIView.as_view(), name="map-overview"),

    # Admin module (Batch B)
    path("admin/", include("monitoring.admin_urls")),

    path("ingest/industry/", IngestIndustryReadingAPIView.as_view(), name="ingest-industry"),

]
