# monitoring/auth_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .firebase_config import root_ref
from .permissions import IsAdmin
from datetime import datetime


def log_admin_action(
    action,
    performed_by="system",
    role="System",
    entity=None,
    before=None,
    after=None,
    approved_by=None,
    severity="Low",
    request=None,
):
    """
    Advanced audit log entry
    """

    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    log_id = f"LOG_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

    ip_address = None
    if request:
        ip_address = request.META.get("REMOTE_ADDR")

    entry = {
        "action": action,
        "performed_by": performed_by,
        "role": role,
        "entity": entity,
        "before": before,
        "after": after,
        "approved_by": approved_by,
        "severity": severity,
        "ip": ip_address,
        "timestamp": timestamp,
    }

    root_ref().child("admin_logs").child(log_id).set(entry)

def _normalise_role(role: str) -> str:
    if not role:
        return ""
    role = role.strip().lower()
    if role in ["admin", "system admin", "sys admin", "system administrator"]:
        return "Admin"
    if role in ["ema", "ema officer", "environmental management agency"]:
        return "EMA Officer"
    if role in ["council", "city council", "urban council", "bcc", "council officer"]:
        return "City Council"
    return role.title()


# ================= LOGIN =================

class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        employee_code = request.data.get("employee_code")
        role = _normalise_role(request.data.get("role"))

        if not all([username, password, employee_code, role]):
            return Response(
                {"error": "Missing required fields (username, password, employee_code, role)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = root_ref().child("users").child(employee_code).get()

        if not user:
            return Response({"error": "Invalid employee code"}, status=status.HTTP_401_UNAUTHORIZED)

        if str(user.get("username", "")).strip() != str(username).strip():
            return Response({"error": "Invalid username"}, status=status.HTTP_401_UNAUTHORIZED)

        if str(user.get("password", "")).strip() != str(password).strip():
            return Response({"error": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)

        if _normalise_role(user.get("role", "")) != role:
            return Response({"error": "Invalid role for this employee code"}, status=status.HTTP_401_UNAUTHORIZED)

        if str(user.get("status", "Active")).strip().lower() != "active":
            return Response({"error": "Account not active"}, status=status.HTTP_403_FORBIDDEN)

        root_ref().child("users").child(employee_code).update({
            "last_login": datetime.utcnow().isoformat() + "Z"
        })

        return Response(
            {
                "message": "Access granted",
                "employee_code": employee_code,
                "role": role,
                "display_name": user.get("name", username),
            },
            status=status.HTTP_200_OK,
        )


# ================= CREATE USER =================

class CreateUserAPIView(APIView):
    authentication_classes = []
    permission_classes = [IsAdmin]

    def post(self, request):
        employee_code = request.data.get("employee_code")
        username = request.data.get("username")
        password = request.data.get("password")
        role = _normalise_role(request.data.get("role"))
        status_value = request.data.get("status", "Active")

        if not all([employee_code, username, password, role]):
            return Response(
                {"error": "Missing required fields"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ref = root_ref().child("users")

        if ref.child(employee_code).get():
            return Response(
                {"error": "Employee code already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        ref.child(employee_code).set({
            "username": username,
            "password": password,
            "role": role,
            "status": status_value,
            "name": username
        })

        # 🔹 Log action
        log_admin_action(
            action="User Created",
            performed_by=request.headers.get("X-User-Role"),
            target_user=employee_code,
            before="-",
            after=f"Created with role {role}, status {status_value}",
            request=request
        )

        return Response(
            {"message": "User created successfully"},
            status=status.HTTP_201_CREATED
        )


# ================= LIST USERS =================

class UsersListAPIView(APIView):
    def get(self, request):
        users = root_ref().child("users").get()

        if not users:
            return Response([], status=status.HTTP_200_OK)

        result = []

        for employee_code, details in users.items():
            payload = dict(details)
            payload["employee_code"] = employee_code
            result.append(payload)

        return Response(result, status=status.HTTP_200_OK)


# ================= UPDATE USER =================

class UpdateUserAPIView(APIView):
    def put(self, request, employee_code):
        ref = root_ref().child("users").child(employee_code)

        user = ref.get()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        old_user = user.copy()

        updated_data = {}

        if "username" in request.data:
            updated_data["username"] = request.data["username"]

        if "password" in request.data:
            updated_data["password"] = request.data["password"]

        if "role" in request.data:
            updated_data["role"] = _normalise_role(request.data["role"])

        if "status" in request.data:
            updated_data["status"] = request.data["status"]

        ref.update(updated_data)

        log_admin_action(
            action="User Updated",
            performed_by=request.headers.get("X-User-Role"),
            target_user=employee_code,
            before=str(old_user),
            after=str({**old_user, **updated_data}),
            request=request
        )


        return Response({"message": "User updated successfully"})


# ================= ADMIN LOGS =================

class AdminLogsAPIView(APIView):
    authentication_classes = []
    permission_classes = [IsAdmin]

    def get(self, request):
        logs = root_ref().child("admin_logs").get()

        if not logs:
            return Response([])

        result = []

        for key, value in logs.items():
            value["id"] = key
            result.append(value)

        return Response(result)
