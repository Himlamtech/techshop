"""
Middleware stack for TechShop Django services.

Provides:
- RequestIDMiddleware: generates/propagates X-Request-ID
- StructuredLoggingMiddleware: logs JSON with timing and context
- JWTAuthenticationMiddleware: extracts and validates JWT tokens
"""

import json
import logging
import time
import uuid

import jwt
from django.conf import settings

from apps.core.request_context import clear_request_context, set_request_context

logger = logging.getLogger(__name__)


class RequestIDMiddleware:
    """
    Generate or propagate a request ID for every incoming request.

    If the incoming request has an X-Request-ID header, use it.
    Otherwise, generate a new one with the format req_<uuid>.
    Stores the request_id on the request object and in thread-local context.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract or generate request ID
        request_id = request.META.get("HTTP_X_REQUEST_ID")
        if not request_id:
            request_id = f"req_{uuid.uuid4().hex}"

        request.request_id = request_id

        # Store in thread-local for access from responses/exceptions
        set_request_context(request_id=request_id)

        response = self.get_response(request)

        # Add request ID to response headers
        response["X-Request-ID"] = request_id

        return response


class StructuredLoggingMiddleware:
    """
    Log every request/response as a structured JSON entry.

    Log fields: timestamp, level, service, request_id, user_id,
    method, path, status_code, duration_ms.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)

        user_id = getattr(request, "user_id", None)
        request_id = getattr(request, "request_id", None)

        log_data = {
            "service": getattr(settings, "SERVICE_NAME", "unknown"),
            "request_id": request_id,
            "user_id": str(user_id) if user_id else None,
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }

        if response.status_code >= 500:
            logger.error("request_completed", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("request_completed", extra=log_data)
        else:
            logger.info("request_completed", extra=log_data)

        return response


class JWTAuthenticationMiddleware:
    """
    Extract and validate JWT from the Authorization header.

    On success, sets request.user_id and request.user_role.
    On failure (missing, expired, invalid), sets both to None
    and lets permission classes handle enforcement.

    Uses the shared public key for RS256 verification.
    """

    # Paths that should skip JWT validation entirely
    PUBLIC_PATHS = [
        "/healthz",
        "/readyz",
        "/admin/",
        "/api/v1/auth/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self._public_key = None

    def _get_public_key(self):
        """Load the JWT public key from file (cached after first load)."""
        if self._public_key is None:
            key_path = getattr(settings, "JWT_PUBLIC_KEY_PATH", None)
            if key_path:
                try:
                    with open(key_path, "r") as f:
                        self._public_key = f.read()
                except (FileNotFoundError, IOError):
                    logger.warning("JWT public key file not found: %s", key_path)
                    self._public_key = ""
        return self._public_key

    def _is_public_path(self, path):
        """Check if the request path is public (no auth needed)."""
        for public_path in self.PUBLIC_PATHS:
            if path.startswith(public_path):
                return True
        return False

    def __call__(self, request):
        request.user_id = None
        request.user_role = None

        if not self._is_public_path(request.path):
            self._extract_jwt(request)

        # Update thread-local context with user info
        set_request_context(
            request_id=getattr(request, "request_id", None),
            user_id=request.user_id,
            user_role=request.user_role,
        )

        response = self.get_response(request)

        # Clear thread-local context after request
        clear_request_context()

        return response

    def _extract_jwt(self, request):
        """Extract and validate JWT from Authorization header."""
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return

        token = auth_header[7:]  # Strip "Bearer " prefix

        public_key = self._get_public_key()
        if not public_key:
            return

        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[getattr(settings, "JWT_ALGORITHM", "RS256")],
                issuer=getattr(settings, "JWT_ISSUER", None),
                options={"verify_exp": True},
            )
            request.user_id = payload.get("user_id")
            request.user_role = payload.get("role")
        except jwt.ExpiredSignatureError:
            logger.debug("JWT token expired")
        except jwt.InvalidTokenError as e:
            logger.debug("JWT validation failed: %s", str(e))
