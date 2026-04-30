from rest_framework.views import APIView
from rest_framework.response import Response
from .firebase_config import root_ref
from .permissions import IsAdmin


class OverridesAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        data = root_ref().child("overrides").get() or {}
        return Response(data)

    def delete(self, request):
        entity = request.data.get("entity")
        entity_type = request.data.get("type").lower()
        parameter = request.data.get("parameter")

        root_ref().child("overrides") \
            .child(entity_type) \
            .child(entity) \
            .child(parameter) \
            .delete()

        return Response({"message": "Override deleted"})

    def post(self, request):
        entity = request.data.get("entity")
        entity_type = request.data.get("type").lower()
        parameter = request.data.get("parameter")
        limit = request.data.get("customLimit")

        root_ref().child("overrides")\
            .child(entity_type)\
            .child(entity)\
            .child(parameter)\
            .set(limit)

        log_admin_action(
            action="Override Created",
            performed_by=request.headers.get("X-User-Role"),
            role=request.headers.get("X-User-Role"),
            entity=f"{entity} - {parameter}",
            before="Default Limit",
            after=str(custom_limit),
            severity="High",
            request=request,
        )

        return Response({"message": "Override saved"})