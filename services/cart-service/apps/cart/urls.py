"""URL configuration for Cart app."""

from django.urls import path

from apps.cart.views import CartDetailView, CartItemDetailView, CartItemListView

urlpatterns = [
    path("current", CartDetailView.as_view(), name="cart-current"),
    path("items", CartItemListView.as_view(), name="cart-items"),
    path("items/<uuid:pk>", CartItemDetailView.as_view(), name="cart-item-detail"),
]
