from django.contrib import admin

from apps.order.models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("id",)


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("id", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_id",
        "status",
        "subtotal",
        "total_amount",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("user_id", "id")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [OrderItemInline, OrderStatusHistoryInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product_name",
        "product_sku",
        "unit_price",
        "quantity",
        "line_total",
    )
    search_fields = ("product_name", "product_sku", "product_id")
    readonly_fields = ("id",)


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "from_status", "to_status", "reason", "created_at")
    list_filter = ("from_status", "to_status")
    search_fields = ("order__id",)
    readonly_fields = ("id", "created_at")
