from django.contrib import admin

from apps.identity.models import RefreshToken, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "is_active", "failed_login_attempts", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("email",)
    readonly_fields = ("id", "password_hash", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_revoked", "expires_at", "created_at")
    list_filter = ("is_revoked",)
    search_fields = ("user__email",)
    readonly_fields = ("id", "token_hash", "created_at")
    ordering = ("-created_at",)
