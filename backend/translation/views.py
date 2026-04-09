"""Public translation endpoint — handy for the frontend chat box."""

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAuthenticatedEmployer

from .service import translate


class TranslateRequest(serializers.Serializer):
    text = serializers.CharField(max_length=5_000)
    target = serializers.CharField(max_length=5)
    source = serializers.CharField(max_length=5, required=False, allow_blank=True)


class TranslateView(APIView):
    permission_classes = [IsAuthenticatedEmployer]

    @extend_schema(
        request=TranslateRequest,
        responses=inline_serializer(
            name="TranslateResponse",
            fields={
                "text": serializers.CharField(),
                "cached": serializers.BooleanField(),
                "fallback": serializers.BooleanField(),
            },
        ),
        description="Translate arbitrary text. Cached in Redis for 7 days.",
    )
    def post(self, request):
        payload = TranslateRequest(data=request.data)
        payload.is_valid(raise_exception=True)
        result = translate(
            text=payload.validated_data["text"],
            target=payload.validated_data["target"],
            source=payload.validated_data.get("source") or None,
        )
        return Response(
            {
                "text": result.text,
                "cached": result.cached,
                "fallback": result.fallback,
            },
            status=status.HTTP_200_OK,
        )
