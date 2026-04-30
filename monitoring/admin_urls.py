# monitoring/admin_urls.py
from django.urls import path

from .compliance_views import ComplianceHistoryAPIView
from .admin_views import (
    AdminUsersAPIView,
    AdminApproveUserAPIView,
    AdminRevokeUserAPIView,
    AdminSensorsAPIView,
    AdminCalibrateSensorAPIView,
    AdminResetSensorAPIView,
    AdminActiveAlertsAPIView,
    AdminResolveAlertAPIView,
    AdminActivityLogAPIView,
    AdminReportsSummaryAPIView,
    AdminExportReportCSVAPIView,
)

urlpatterns = [

    path("compliance-history/", ComplianceHistoryAPIView.as_view()),
    # Users
    path("users/", AdminUsersAPIView.as_view(), name="admin_users"),
    path("users/approve/", AdminApproveUserAPIView.as_view(), name="admin_users_approve"),
    path("users/revoke/", AdminRevokeUserAPIView.as_view(), name="admin_users_revoke"),

    # Sensors
    path("sensors/", AdminSensorsAPIView.as_view(), name="admin_sensors"),
    path("sensors/calibrate/", AdminCalibrateSensorAPIView.as_view(), name="admin_sensors_calibrate"),
    path("sensors/reset/", AdminResetSensorAPIView.as_view(), name="admin_sensors_reset"),

    # Alerts + Logs
    path("alerts/active/", AdminActiveAlertsAPIView.as_view(), name="admin_alerts_active"),
    path("alerts/resolve/", AdminResolveAlertAPIView.as_view(), name="admin_alerts_resolve"),
    path("activity-log/", AdminActivityLogAPIView.as_view(), name="admin_activity_log"),

    # Reports
    path("reports/summary/", AdminReportsSummaryAPIView.as_view(), name="admin_reports_summary"),
    path("reports/export/csv/", AdminExportReportCSVAPIView.as_view(), name="admin_reports_export_csv"),
]
