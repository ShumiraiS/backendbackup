from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .firebase import root_ref

class LoginAPIView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        role = request.data.get("role")
        employee_code = request.data.get("employee_code")

        if not all([username, password, role, employee_code]):
            return Response(
                {"error": "Missing required fields"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = root_ref().child("users").child(employee_code).get()

        if not user:
            return Response(
                {"error": "Invalid employee code"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if user.get("active") is not True:
            return Response(
                {"error": "Account inactive"},
                status=status.HTTP_403_FORBIDDEN
            )

        if (
            user.get("username") == username and
            user.get("password") == password and
            user.get("role") == role
        ):
            return Response(
                {"message": "Access granted", "role": user.get("role")},
                status=status.HTTP_200_OK
            )

        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )
