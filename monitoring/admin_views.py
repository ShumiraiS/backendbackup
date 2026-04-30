# monitoring/admin_views.py
from datetime import datetime, timedelta, timezone
import json

from django.http import JsonResponse, HttpResponse
from django.views import View

from .firebase import root_ref


# -----------------------------
# Helpers
# -----------------------------
def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(ts: str):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _make_log(actor: str, action: str, details: dict | None = None):
    log_id = f"LOG_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    root_ref().child("activity_log").child(log_id).set({
        "actor": actor,
        "action": action,
        "details": details or {},
        "timestamp": _now_iso()
    })


def _get_thresholds_flat():
    """
    Supports either:
      thresholds.flat (preferred in our master)
    or falls back to:
      thresholds.industry / thresholds.stp (merged)
    """
    try:
        th = root_ref().child("thresholds").get() or {}
    except Exception:
        thresholds = {}

    flat = th.get("flat")
    if isinstance(flat, dict) and flat:
        return flat

    merged = {}
    for section in ("industry", "stp"):
        sec = th.get(section) or {}
        if isinstance(sec, dict):
            for k, v in sec.items():
                merged.setdefault(k, v)
    return merged


def _param_status(param_key: str, value, limits: dict):
    """
    limits example:
      "ph": {"min": 6.5, "max": 8.5}
      "cod": {"max": 60}
    """
    if value is None:
        return "RED"

    rule = limits.get(param_key) or {}
    try:
        val = float(value)
    except Exception:
        return "RED"

    mn = rule.get("min")
    mx = rule.get("max")

    if mn is not None and val < float(mn):
        return "RED"
    if mx is not None and val > float(mx):
        return "RED"
    return "GREEN"


def _overall_compliance(latest: dict, limits: dict):
    keys = ["ph", "temperature", "cod", "chlorides", "suspended_solids"]
    per = {}
    reds = 0
    for k in keys:
        per[k] = _param_status(k, (latest or {}).get(k), limits)
        if per[k] == "RED":
            reds += 1
    return ("RED" if reds > 0 else "GREEN"), per


def _latest_snapshots():
    """
    Returns two dicts:
      ind_latest: {IND_A: latest_reading_dict}
      stp_latest: {STP_1: latest_reading_dict}
    Supports both:
      readings/<id>/latest
      readings_stp/<id>/latest
    """
    db = root_ref()
    ind_latest = {}
    stp_latest = {}

    r = db.child("readings").get() or {}
    if isinstance(r, dict):
        for site_id, payload in r.items():
            if isinstance(payload, dict):
                ind_latest[site_id] = payload.get("latest") or {}
    rs = db.child("readings_stp").limit_to_last(20).get() or {}
    if isinstance(rs, dict):
        for site_id, payload in rs.items():
            if isinstance(payload, dict):
                stp_latest[site_id] = payload.get("latest") or {}

    return ind_latest, stp_latest


# -----------------------------
# ADMIN: Users (Batch 1 support)
# -----------------------------
class AdminUsersAPIView(View):
    """
    GET /api/admin/users/
    """
    def get(self, request):
        try:
            users = root_ref().child("users").get() or {}
        except Exception:
            users = {}

        items = []
        if isinstance(users, dict):
            for employee_code, u in users.items():
                if not isinstance(u, dict):
                    continue
                items.append({
                    "employee_code": employee_code,
                    "name": u.get("name", ""),
                    "email": u.get("email", ""),
                    "username": u.get("username", ""),
                    "role": u.get("role", ""),
                    "status": u.get("status", "Pending"),
                    "last_login": u.get("last_login")
                })
        return JsonResponse({"count": len(items), "items": items})


class AdminApproveUserAPIView(View):
    """
    POST /api/admin/users/approve/
    Body: {"employee_code":"PETER001","actor":"ADMIN001"}
    """
    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        code = payload.get("employee_code")
        actor = payload.get("actor", "ADMIN")

        if not code:
            return JsonResponse({"error": "employee_code is required"}, status=400)

        ref = root_ref().child("users").child(code)
        u = ref.get()
        if not u:
            return JsonResponse({"error": "User not found"}, status=404)

        ref.update({"status": "Active", "active": True})
        _make_log(actor, "APPROVE_USER", {"employee_code": code})
        return JsonResponse({"status": "ok"})


class AdminRevokeUserAPIView(View):
    """
    POST /api/admin/users/revoke/
    Body: {"employee_code":"EMA123","actor":"ADMIN001"}
    """
    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        code = payload.get("employee_code")
        actor = payload.get("actor", "ADMIN")

        if not code:
            return JsonResponse({"error": "employee_code is required"}, status=400)

        ref = root_ref().child("users").child(code)
        u = ref.get()
        if not u:
            return JsonResponse({"error": "User not found"}, status=404)

        ref.update({"status": "Revoked", "active": False})
        _make_log(actor, "REVOKE_USER", {"employee_code": code})
        return JsonResponse({"status": "ok"})


# -----------------------------
# ADMIN: Sensors (Batch 1 support)
# -----------------------------
class AdminSensorsAPIView(View):
    """
    GET /api/admin/sensors/?group=industry|stp
    """
    def get(self, request):
        group = request.GET.get("group", "industry")
        if group not in ("industry", "stp"):
            return JsonResponse({"error": "group must be industry or stp"}, status=400)

        try:
            sensors = root_ref().child("sensors").get() or {}
        except Exception:
            sensors = {}

        items = []
        if isinstance(sensors, dict):
            for sensor_id, s in sensors.items():
                if not isinstance(s, dict):
                    continue
                items.append({
                    "sensor_id": sensor_id,
                    "parameter": s.get("parameter", ""),
                    "location": s.get("location", ""),
                    "status": s.get("status", "Offline"),
                    "last_seen": s.get("last_seen"),
                    "last_reading": s.get("last_reading"),
                    "calibration_offset": s.get("calibration_offset", 0.0)
                })

        return JsonResponse({"count": len(items), "items": items})


class AdminCalibrateSensorAPIView(View):
    """
    POST /api/admin/sensors/calibrate/
    Body: {"group":"industry","sensor_id":"IND-PH-1","offset":0.1,"actor":"ADMIN001"}
    """
    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        group = payload.get("group")
        sensor_id = payload.get("sensor_id")
        actor = payload.get("actor", "ADMIN")
        offset = payload.get("offset")

        if group not in ("industry", "stp") or not sensor_id or offset is None:
            return JsonResponse({"error": "group, sensor_id, offset required"}, status=400)

        ref = root_ref().child("sensors").child(group).child(sensor_id)
        existing = ref.get()
        if not existing:
            return JsonResponse({"error": "Sensor not found"}, status=404)

        try:
            offset_f = float(offset)
        except Exception:
            return JsonResponse({"error": "offset must be a number"}, status=400)

        ref.update({"calibration_offset": offset_f})
        _make_log(actor, "CALIBRATE_SENSOR", {"group": group, "sensor_id": sensor_id, "offset": offset_f})
        return JsonResponse({"status": "ok"})


class AdminResetSensorAPIView(View):
    """
    POST /api/admin/sensors/reset/
    Body: {"group":"industry","sensor_id":"IND-PH-1","actor":"ADMIN001"}
    """
    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        group = payload.get("group")
        sensor_id = payload.get("sensor_id")
        actor = payload.get("actor", "ADMIN")

        if group not in ("industry", "stp") or not sensor_id:
            return JsonResponse({"error": "group and sensor_id required"}, status=400)

        ref = root_ref().child("sensors").child(group).child(sensor_id)
        existing = ref.get()
        if not existing:
            return JsonResponse({"error": "Sensor not found"}, status=404)

        ref.update({
            "calibration_offset": 0.0,
            "status": "Active",
            "last_seen": _now_iso()
        })
        _make_log(actor, "RESET_SENSOR", {"group": group, "sensor_id": sensor_id})
        return JsonResponse({"status": "ok"})


# -----------------------------
# ADMIN: Alerts (Batch B)
# -----------------------------
class AdminActiveAlertsAPIView(View):
    """
    GET /api/admin/alerts/active/
    """
    def get(self, request):
        try:
            alerts = root_ref().child("alerts").get() or {}
        except Exception:
            alerts = {}

        items = []

        if isinstance(alerts, dict):
            for scope, scope_data in alerts.items():
                if not isinstance(scope_data, dict):
                    continue
                for location_id, loc_alerts in scope_data.items():
                    if not isinstance(loc_alerts, dict):
                        continue
                    for alert_id, a in loc_alerts.items():
                        if not isinstance(a, dict):
                            continue
                        read = a.get("read", False)
                        resolved = a.get("resolved", False)
                        if (read is False) and (resolved is False):
                            items.append({
                                "id": alert_id,
                                "scope": scope,
                                "location_id": location_id,
                                "severity": a.get("severity", "HIGH"),
                                "message": a.get("message", ""),
                                "parameters": a.get("parameters", []),
                                "timestamp": a.get("timestamp", "")
                            })

        def sk(x):
            dt = _parse_iso(x.get("timestamp"))
            return dt or datetime(1970, 1, 1, tzinfo=timezone.utc)

        items.sort(key=sk, reverse=True)
        return JsonResponse({"count": len(items), "items": items})


class AdminResolveAlertAPIView(View):
    """
    POST /api/admin/alerts/resolve/
    Body: {"scope":"industry","location_id":"IND_A","alert_id":"ALERT_001","actor":"ADMIN001"}
    """
    def post(self, request):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        scope = payload.get("scope")
        location_id = payload.get("location_id")
        alert_id = payload.get("alert_id")
        actor = payload.get("actor", "ADMIN")

        if not scope or not location_id or not alert_id:
            return JsonResponse({"error": "scope, location_id, alert_id required"}, status=400)

        ref = root_ref().child("alerts").child(scope).child(location_id).child(alert_id)
        existing = ref.get()
        if not existing:
            return JsonResponse({"error": "Alert not found"}, status=404)

        ref.update({"resolved": True, "read": True, "resolved_at": _now_iso()})
        _make_log(actor, "ALERT_RESOLVED", {"scope": scope, "location_id": location_id, "alert_id": alert_id})
        return JsonResponse({"status": "ok"})


# -----------------------------
# ADMIN: Activity Log (Batch B)
# -----------------------------
class AdminActivityLogAPIView(View):
    """
    GET /api/admin/activity-log/
    """
    def get(self, request):
        logs = root_ref().child("activity_log").get() or {}
        items = []

        if isinstance(logs, dict):
            for log_id, entry in logs.items():
                if not isinstance(entry, dict):
                    continue
                items.append({
                    "id": log_id,
                    "actor": entry.get("actor", ""),
                    "action": entry.get("action", ""),
                    "details": entry.get("details", {}),
                    "timestamp": entry.get("timestamp", "")
                })

        def sk(x):
            dt = _parse_iso(x.get("timestamp"))
            return dt or datetime(1970, 1, 1, tzinfo=timezone.utc)

        items.sort(key=sk, reverse=True)
        return JsonResponse({"count": len(items), "items": items})


# -----------------------------
# ADMIN: Reports (Batch B)
# -----------------------------
class AdminReportsSummaryAPIView(View):
    """
    GET /api/admin/reports/summary/?window_hours=24
    """
    def get(self, request):
        try:
            window_hours = int(request.GET.get("window_hours", "24"))
        except Exception:
            window_hours = 24

        start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        limits = _get_thresholds_flat()
        ind_latest, stp_latest = _latest_snapshots()

        # alerts today + active alerts
        alerts = root_ref().child("alerts").get() or {}
        alerts_today = 0
        active_alerts = 0

        if isinstance(alerts, dict):
            for scope, scope_data in alerts.items():
                if not isinstance(scope_data, dict):
                    continue
                for _, loc_alerts in scope_data.items():
                    if not isinstance(loc_alerts, dict):
                        continue
                    for _, a in loc_alerts.items():
                        if not isinstance(a, dict):
                            continue
                        dt = _parse_iso(a.get("timestamp"))
                        if dt and dt >= start:
                            alerts_today += 1
                        if a.get("resolved", False) is False and a.get("read", False) is False:
                            active_alerts += 1

        # compliance rate from latest snapshots
        total = 0
        compliant = 0

        scores = {k: [] for k in ["ph", "temperature", "cod", "chlorides", "suspended_solids"]}

        def handle(latest):
            nonlocal total, compliant
            if not isinstance(latest, dict) or not latest:
                return
            total += 1
            overall, per = _overall_compliance(latest, limits)
            if overall == "GREEN":
                compliant += 1
            for k, v in per.items():
                scores[k].append(100 if v == "GREEN" else 0)

        for _, v in ind_latest.items():
            handle(v)
        for _, v in stp_latest.items():
            handle(v)

        compliance_rate = round((compliant / total * 100), 1) if total else 0.0

        def avg(lst):
            return round(sum(lst) / len(lst), 1) if lst else 0.0

        param_perf = {k: avg(v) for k, v in scores.items()}
        avg_perf = round(sum(param_perf.values()) / 5, 1)

        # sensors monitored
        sensors = root_ref().child("sensors").get() or {}
        total_sensors = 0
        active_sensors = 0
        if isinstance(sensors, dict):
            for grp in ("industry", "stp"):
                grp_data = sensors.get(grp) or {}
                if isinstance(grp_data, dict):
                    for _, s in grp_data.items():
                        total_sensors += 1
                        if isinstance(s, dict) and s.get("status") == "Active":
                            active_sensors += 1

        return JsonResponse({
            "cards": {
                "compliance_rate": compliance_rate,
                "active_sensors": f"{active_sensors}/{total_sensors}",
                "alerts_today": alerts_today,
                "avg_performance": avg_perf,
                "active_alerts": active_alerts
            },
            "parameter_performance": param_perf
        })


class AdminExportReportCSVAPIView(View):
    """
    GET /api/admin/reports/export/csv/
    Exports a simple CSV of latest readings + compliance.
    """
    def get(self, request):
        limits = _get_thresholds_flat()
        ind_latest, stp_latest = _latest_snapshots()

        header = [
            "scope", "location_id", "timestamp",
            "ph", "temperature", "cod", "chlorides", "suspended_solids",
            "overall_status"
        ]
        lines = [",".join(header)]

        def add(scope, data):
            for location_id, latest in data.items():
                if not isinstance(latest, dict) or not latest:
                    continue
                overall, _ = _overall_compliance(latest, limits)
                lines.append(",".join([
                    scope,
                    location_id,
                    str(latest.get("timestamp", "")),
                    str(latest.get("ph", "")),
                    str(latest.get("temperature", "")),
                    str(latest.get("cod", "")),
                    str(latest.get("chlorides", "")),
                    str(latest.get("suspended_solids", "")),
                    overall
                ]))

        add("industry", ind_latest)
        add("stp", stp_latest)

        csv_content = "\n".join(lines)
        resp = HttpResponse(csv_content, content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="effluai_report.csv"'
        return resp
