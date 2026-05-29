"""
Authentication views for the Identity Service.

All endpoints are public (no authentication required).
Business logic is delegated to AuthService.
"""

import logging

from rest_framework.views import APIView

from apps.core.exceptions import UnauthorizedError
from apps.core.responses import error_response, success_response
from apps.identity.serializers import LoginSerializer, RefreshSerializer, RegisterSerializer
from apps.identity.services import AccountLockedError, AuthService

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    POST /api/v1/auth/register

    Create a new user account with the customer role.
    Returns access and refresh tokens on success.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code="VALIDATION_ERROR",
                message="Invalid registration data.",
                details=_format_serializer_errors(serializer.errors),
                status=422,
            )

        result = AuthService.register(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        return success_response(data=result, status=201)


class LoginView(APIView):
    """
    POST /api/v1/auth/login

    Authenticate a user with email and password.
    Returns access and refresh tokens on success.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code="VALIDATION_ERROR",
                message="Invalid login data.",
                details=_format_serializer_errors(serializer.errors),
                status=422,
            )

        try:
            result = AuthService.login(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        except AccountLockedError as e:
            return error_response(
                code="ACCOUNT_LOCKED",
                message=e.message,
                status=423,
            )
        except UnauthorizedError as e:
            return error_response(
                code="UNAUTHORIZED",
                message=e.message,
                status=401,
            )

        return success_response(data=result)


class RefreshView(APIView):
    """
    POST /api/v1/auth/refresh

    Validate a refresh token and issue a new token pair.
    The old refresh token is invalidated (token rotation).
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                code="VALIDATION_ERROR",
                message="Invalid refresh token data.",
                details=_format_serializer_errors(serializer.errors),
                status=422,
            )

        try:
            result = AuthService.refresh(
                refresh_token_value=serializer.validated_data["refresh_token"],
            )
        except UnauthorizedError as e:
            return error_response(
                code="UNAUTHORIZED",
                message=e.message,
                status=401,
            )

        return success_response(data=result)


def _format_serializer_errors(errors):
    """Convert DRF serializer errors to standard details format."""
    details = []
    for field, messages in errors.items():
        for message in messages:
            details.append({"field": field, "reason": str(message)})
    return details
