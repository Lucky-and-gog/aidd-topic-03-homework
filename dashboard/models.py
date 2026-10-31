from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
User = get_user_model()

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
class Portfolio(models.Model):
    """Инвестиционный портфель пользователя."""

    name = models.CharField(max_length=255, verbose_name="Название портфеля")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="portfolios", verbose_name="Пользователь"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        unique_together = ("user", "name")
        verbose_name = "Портфель"
        verbose_name_plural = "Портфели"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user})"


class Position(models.Model):
    """Позиция по акции в портфеле."""

    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="positions", verbose_name="Портфель"
    )
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="positions", verbose_name="Акция"
    )
    quantity = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0"), verbose_name="Количество"
    )
    average_price = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0"), verbose_name="Средняя цена"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        unique_together = ("portfolio", "share")
        verbose_name = "Позиция"
        verbose_name_plural = "Позиции"

    def __str__(self):
        return f"{self.share.ticker}: {self.quantity}"

    @property
    def market_value(self):
        if self.share.last_price is None:
            return Decimal("0")
        return self.quantity * Decimal(str(self.share.last_price))

    @property
    def cost_basis(self):
        return self.quantity * self.average_price

    @property
    def unrealized_pnl(self):
        return self.market_value - self.cost_basis


class PortfolioTransaction(models.Model):
    """Операция покупки/продажи в портфеле."""

    OPERATION_BUY = "BUY"
    OPERATION_SELL = "SELL"
    OPERATION_CHOICES = [
        (OPERATION_BUY, "Покупка"),
        (OPERATION_SELL, "Продажа"),
    ]

    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="transactions", verbose_name="Портфель"
    )
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="transactions", verbose_name="Акция"
    )
    operation = models.CharField(
        max_length=4, choices=OPERATION_CHOICES, verbose_name="Операция"
    )
    quantity = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="Количество")
    price = models.DecimalField(max_digits=18, decimal_places=4, verbose_name="Цена")
    realized_pnl = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0"), verbose_name="Реализованная прибыль/убыток"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата операции")

    class Meta:
        verbose_name = "Операция"
        verbose_name_plural = "Операции"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_operation_display()} {self.share.ticker} x{self.quantity}"
