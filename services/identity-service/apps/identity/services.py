"""
Authentication service layer for the Identity Service.

Contains all business logic for registration, login, token refresh,
account lockout, and JWT token generation.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password

from apps.core.exceptions import UnauthorizedError, ValidationError
from apps.identity.models import RefreshToken, User

logger = logging.getLogger(__name__)


class AccountLockedError(Exception):
    """Raised when an account is temporarily locked due to failed login attempts."""

    error_code = "ACCOUNT_LOCKED"
    http_status = 423
    message = "Account is temporarily locked due to too many failed login attempts"

    def __init__(self, message=None):
        self.message = message or self.__class__.message
        super().__init__(self.message)


class AuthService:
    """Handles authentication business logic."""

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    FAILED_ATTEMPT_WINDOW_MINUTES = 15

    @classmethod
    def register(cls, email, password):
        """
        Register a new user with the customer role.

        Args:
            email: Valid email address.
            password: Password (8-128 chars).

        Returns:
            dict with access_token, refresh_token, and user info.

        Raises:
            ValidationError: If email already exists.
        """
        # Check for existing user
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                message="A user with this email already exists.",
                details=[{"field": "email", "reason": "Email already registered."}],
            )

        # Create user with hashed password
        user = User.objects.create(
            email=email,
            password_hash=make_password(password),
            role=User.Role.CUSTOMER,
        )

        # Generate tokens
        tokens = cls._generate_tokens(user)

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
            },
        }

    @classmethod
    def login(cls, email, password):
        """
        Authenticate a user and return tokens.

        Args:
            email: User's email address.
            password: User's password.

        Returns:
            dict with access_token, refresh_token, and user info.

        Raises:
            UnauthorizedError: If credentials are invalid.
            AccountLockedError: If account is locked.
        """
        # Look up user - use generic error to not reveal which field is wrong
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise UnauthorizedError(message="Invalid email or password.")

        # Check if account is locked
        cls._check_lockout(user)

        # Validate password
        if not check_password(password, user.password_hash):
            cls._record_failed_attempt(user)
            raise UnauthorizedError(message="Invalid email or password.")

        # Successful login - reset failed attempts
        cls._reset_failed_attempts(user)

        # Generate tokens
        tokens = cls._generate_tokens(user)

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
            },
        }

    @classmethod
    def refresh(cls, refresh_token_value):
        """
        Validate a refresh token and issue a new token pair.

        Args:
            refresh_token_value: The raw refresh token string.

        Returns:
            dict with new access_token, refresh_token, and user info.

        Raises:
            UnauthorizedError: If refresh token is invalid, expired, or revoked.
        """
        # Hash the provided token to look it up
        token_hash = cls._hash_token(refresh_token_value)

        try:
            refresh_token = RefreshToken.objects.select_related("user").get(
                token_hash=token_hash
            )
        except RefreshToken.DoesNotExist:
            raise UnauthorizedError(message="Invalid refresh token.")

        # Check if revoked
        if refresh_token.is_revoked:
            raise UnauthorizedError(message="Refresh token has been revoked.")

        # Check if expired
        now = datetime.now(timezone.utc)
        if refresh_token.expires_at < now:
            raise UnauthorizedError(message="Refresh token has expired.")

        # Revoke the old refresh token (token rotation)
        refresh_token.is_revoked = True
        refresh_token.save(update_fields=["is_revoked"])

        # Generate new token pair
        user = refresh_token.user
        tokens = cls._generate_tokens(user)

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
            },
        }

    @classmethod
    def _generate_tokens(cls, user):
        """
        Generate JWT access token and refresh token for a user.

        Access token: JWT with user_id, role, iss, exp (15 min).
        Refresh token: random string, hashed and stored in DB (7 days).

        Falls back to HS256 with SECRET_KEY if RSA private key is unavailable.
        """
        now = datetime.now(timezone.utc)

        # Build access token payload
        access_payload = {
            "user_id": str(user.id),
            "role": user.role,
            "iss": settings.JWT_ISSUER,
            "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_LIFETIME_MINUTES),
            "iat": now,
        }

        # Determine signing key and algorithm
        private_key = cls._get_private_key()
        if private_key:
            algorithm = settings.JWT_ALGORITHM  # RS256
            signing_key = private_key
        else:
            # Fallback to HS256 for development without RSA keys
            algorithm = "HS256"
            signing_key = settings.SECRET_KEY

        access_token = jwt.encode(access_payload, signing_key, algorithm=algorithm)

        # Generate refresh token (random string)
        raw_refresh_token = secrets.token_urlsafe(64)
        token_hash = cls._hash_token(raw_refresh_token)

        # Store hashed refresh token in DB
        RefreshToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=now + timedelta(days=settings.JWT_REFRESH_TOKEN_LIFETIME_DAYS),
        )

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh_token,
        }

    @classmethod
    def _check_lockout(cls, user):
        """
        Check if the user's account is currently locked.

        Raises:
            AccountLockedError: If the account is locked.
        """
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise AccountLockedError()

    @classmethod
    def _record_failed_attempt(cls, user):
        """
        Record a failed login attempt and lock the account if threshold is reached.

        Logic:
        - Increment failed_login_attempts.
        - If attempts >= 5, lock the account for 15 minutes.
        """
        now = datetime.now(timezone.utc)

        # If the lockout window has passed, reset the counter first
        if user.locked_until and user.locked_until <= now:
            user.failed_login_attempts = 0
            user.locked_until = None

        user.failed_login_attempts += 1

        if user.failed_login_attempts >= cls.MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=cls.LOCKOUT_DURATION_MINUTES)
            logger.warning(
                "Account locked due to failed attempts",
                extra={"user_id": str(user.id), "email": user.email},
            )

        user.save(update_fields=["failed_login_attempts", "locked_until"])

    @classmethod
    def _reset_failed_attempts(cls, user):
        """Reset failed login attempts on successful login."""
        if user.failed_login_attempts > 0 or user.locked_until:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_attempts", "locked_until"])

    @classmethod
    def _hash_token(cls, token):
        """Hash a refresh token using SHA-256 for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def _get_private_key(cls):
        """Load the JWT private key from file. Returns None if unavailable."""
        key_path = getattr(settings, "JWT_PRIVATE_KEY_PATH", None)
        if not key_path:
            return None
        try:
            with open(key_path, "r") as f:
                return f.read()
        except (FileNotFoundError, IOError):
            logger.debug("JWT private key file not found: %s", key_path)
            return None
