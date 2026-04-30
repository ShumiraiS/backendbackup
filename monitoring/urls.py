# monitoring/urls.py
from django.urls import path, include
from .thresholds_views import ThresholdsAPIView
from .auth_views import LoginAPIView
from .industries_views import IndustriesListAPIView
from .readings_views import LatestReadingByIndustryAPIView
from .stps_views import STPsListAPIView
from .stp_readings_views import LatestReadingBySTPAPIView
from .ai_views import AIAdviceAPIView
from .alerts_views import AlertsListAPIView, MarkAlertReadAPIView
from .map_views import MapOverviewAPIView
from .ingest_views import IngestIndustryReadingAPIView
from .auth_views import CreateUserAPIView
from .auth_views import UsersListAPIView
from .sensors_views import SensorsAPIView
from .limits_views import OverridesAPIView
from .audit_views import AuditLogsAPIView
from .reports_views import ReportsSummaryAPIView
from .dashboard_views import DashboardOverviewView
from monitoring.system_views import SystemHealthAPIView
from .monitoring_views import MonitoringRecordsAPIView
from .auth_views import (
    UpdateUserAPIView,
    AdminLogsAPIView,
)





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

    path("readings/stp/latest/", LatestReadingBySTPAPIView.as_view()),


    # Admin module (Batch B)
    path("admin/", include("monitoring.admin_urls")),

    path("ingest/industry/", IngestIndustryReadingAPIView.as_view(), name="ingest-industry"),
    path("users/create/", CreateUserAPIView.as_view()),
    path("users/", UsersListAPIView.as_view()),
    path("users/update/<str:employee_code>/", UpdateUserAPIView.as_view()),
    path("admin/logs/", AdminLogsAPIView.as_view()),
    path("sensors/", SensorsAPIView.as_view()),
    path("thresholds/", ThresholdsAPIView.as_view()),
    path("limits/overrides/", OverridesAPIView.as_view()),
    path("monitoring-records/", MonitoringRecordsAPIView.as_view()),
    path("admin/logs/", AuditLogsAPIView.as_view()),
    path("reports/summary/", ReportsSummaryAPIView.as_view()),
    path("dashboard/overview/", DashboardOverviewView.as_view()),
    path("admin/system-health/", SystemHealthAPIView.as_view()),




]
