from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.headers.get("X-User-Role") == "Admin"


class IsEMA(BasePermission):
    def has_permission(self, request, view):
        return request.headers.get("X-User-Role") == "EMA Officer"
