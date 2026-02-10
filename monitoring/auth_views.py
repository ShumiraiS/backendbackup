# monitoring/auth_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .firebase_config import root_ref


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


class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        employee_code = request.data.get("employee_code")
        role = _normalise_role(request.data.get("role"))

        # Require role selection (as you requested)
        if not all([username, password, employee_code, role]):
            return Response(
                {"error": "Missing required fields (username, password, employee_code, role)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ref = root_ref()
        user = root_ref().child("Users").child("users").child(employee_code).get()


        if not user:
            return Response({"error": "Invalid employee code"}, status=status.HTTP_401_UNAUTHORIZED)

        # expected structure in Firebase:
        # users:
        #   ADMIN001:
        #     username: "admin_user"
        #     password: "password123"
        #     role: "Admin"
        #     status: "Active"

        if str(user.get("username", "")).strip() != str(username).strip():
            return Response({"error": "Invalid username"}, status=status.HTTP_401_UNAUTHORIZED)

        if str(user.get("password", "")).strip() != str(password).strip():
            return Response({"error": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)

        if _normalise_role(user.get("role", "")) != role:
            return Response({"error": "Invalid role for this employee code"}, status=status.HTTP_401_UNAUTHORIZED)

        if str(user.get("status", "Active")).strip().lower() != "active":
            return Response({"error": "Account not active"}, status=status.HTTP_403_FORBIDDEN)

        return Response(
            {
                "message": "Access granted",
                "employee_code": employee_code,
                "role": role,
                "display_name": user.get("name", username),
            },
            status=status.HTTP_200_OK,
        )
