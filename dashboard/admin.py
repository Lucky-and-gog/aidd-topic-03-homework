from django.contrib import admin

from dashboard.models import (
    Portfolio,
    PortfolioTransaction,
    Position,
    Share,
)


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("figi", "isin", "name", "ticker", "currency")
    search_fields = ("figi", "isin", "name", "ticker")
    fields = (
        "figi",
        "isin",
        "name",
        "ticker",
        "currency",
        "uid",
        "last_price",
        "is_trend_high",
    )


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")
    search_fields = ("name", "user__email")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("portfolio", "share", "quantity", "average_price")
    list_filter = ("portfolio",)
    search_fields = ("portfolio__name", "share__ticker", "share__name")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PortfolioTransaction)
class PortfolioTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "portfolio",
        "share",
        "operation",
        "quantity",
        "price",
        "realized_pnl",
    )
    list_filter = ("operation", "portfolio")
    search_fields = ("portfolio__name", "share__ticker", "share__name")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
