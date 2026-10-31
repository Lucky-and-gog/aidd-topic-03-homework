from decimal import Decimal

from django.conf import settings
from django.db import models


class Share(models.Model):
    """Акция"""

    figi = models.CharField(max_length=255, unique=True)
    isin = models.CharField(max_length=255)
    name = models.CharField(max_length=255, verbose_name="Наименование компании")
    ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
    currency = models.CharField(max_length=20, verbose_name="Валюта")
    uid = models.CharField(max_length=255, unique=True)
    last_price = models.FloatField(blank=True, null=True, verbose_name="Текущая цена")
    is_trend_high = models.BooleanField(
        blank=True, null=True, verbose_name="Растет цена"
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"

    def __str__(self):
        return f"{self.ticker} — {self.name}"


class Portfolio(models.Model):
    """Персональный инвестиционный портфель пользователя."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
        verbose_name="Пользователь",
    )
    name = models.CharField(max_length=255, verbose_name="Название портфеля")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата создания"
    )

    class Meta:
        verbose_name = "Портфель"
        verbose_name_plural = "Портфели"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_user_portfolio_name"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.user})"

    @property
    def invested_value(self):
        return sum(
            (position.cost_basis for position in self.positions.all()),
            Decimal("0"),
        )

    @property
    def current_value(self):
        return sum(
            (position.current_value for position in self.positions.all()),
            Decimal("0"),
        )

    @property
    def realized_pnl(self):
        return sum(
            (transaction.realized_pnl for transaction in self.transactions.all()),
            Decimal("0"),
        )

    @property
    def unrealized_pnl(self):
        return self.current_value - self.invested_value

    @property
    def total_pnl(self):
        return self.realized_pnl + self.unrealized_pnl

    @property
    def total_pnl_percent(self):
        if self.invested_value == 0:
            return Decimal("0")
        return (self.total_pnl / self.invested_value) * Decimal("100")


class Position(models.Model):
    """Текущая позиция по акции внутри портфеля."""

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="Портфель",
    )
    share = models.ForeignKey(
        Share,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="Акция",
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        default=Decimal("0"),
        verbose_name="Количество",
    )
    average_price = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0"),
        verbose_name="Средняя цена приобретения",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Позиция"
        verbose_name_plural = "Позиции"
        ordering = ["share__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["portfolio", "share"], name="unique_portfolio_share"
            )
        ]

    def __str__(self):
        return f"{self.portfolio.name}: {self.share.ticker} x {self.quantity}"

    @property
    def market_price(self):
        if self.share.last_price is not None:
            return Decimal(str(self.share.last_price))
        return self.average_price

    @property
    def cost_basis(self):
        return self.quantity * self.average_price

    @property
    def current_value(self):
        return self.quantity * self.market_price

    @property
    def unrealized_pnl(self):
        return self.current_value - self.cost_basis


class PortfolioTransaction(models.Model):
    """История операций покупки и продажи акций."""

    class Operation(models.TextChoices):
        BUY = "BUY", "Покупка"
        SELL = "SELL", "Продажа"

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Портфель",
    )
    share = models.ForeignKey(
        Share,
        on_delete=models.CASCADE,
        related_name="portfolio_transactions",
        verbose_name="Акция",
    )
    operation = models.CharField(
        max_length=4, choices=Operation.choices, verbose_name="Операция"
    )
    quantity = models.DecimalField(
        max_digits=20, decimal_places=6, verbose_name="Количество"
    )
    price = models.DecimalField(
        max_digits=20, decimal_places=4, verbose_name="Цена за единицу"
    )
    realized_pnl = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        default=Decimal("0"),
        verbose_name="Реализованная прибыль",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата операции"
    )

    class Meta:
        verbose_name = "Операция"
        verbose_name_plural = "Операции"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return (
            f"{self.get_operation_display()} {self.share.ticker} "
            f"x {self.quantity} @ {self.price}"
        )

    @property
    def total(self):
        return self.quantity * self.price
