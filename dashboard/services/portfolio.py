from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from dashboard.models import PortfolioTransaction, Position

MONEY_QUANT = Decimal("0.0001")


@transaction.atomic
def execute_transaction(portfolio, share, operation, quantity, price):
    """Применяет операцию к позиции и сохраняет её в истории.

    Средняя цена рассчитывается методом средней стоимости. При продаже
    реализованная прибыль фиксируется в операции.
    """
    quantity = Decimal(quantity)
    price = Decimal(price)

    if operation not in (
        PortfolioTransaction.Operation.BUY,
        PortfolioTransaction.Operation.SELL,
    ):
        raise ValidationError("Неизвестная операция")
    if quantity <= 0:
        raise ValidationError("Количество должно быть больше нуля")
    if price <= 0:
        raise ValidationError("Цена должна быть больше нуля")

    position, _ = Position.objects.select_for_update().get_or_create(
        portfolio=portfolio,
        share=share,
        defaults={"quantity": Decimal("0"), "average_price": Decimal("0")},
    )

    if (
        operation == PortfolioTransaction.Operation.SELL
        and quantity > position.quantity
    ):
        raise ValidationError(
            f"Недостаточно акций для продажи: доступно {position.quantity}"
        )

    realized_pnl = Decimal("0")

    if operation == PortfolioTransaction.Operation.BUY:
        total_cost = position.quantity * position.average_price + quantity * price
        new_quantity = position.quantity + quantity
        position.average_price = (total_cost / new_quantity).quantize(MONEY_QUANT)
        position.quantity = new_quantity
    else:
        realized_pnl = ((price - position.average_price) * quantity).quantize(
            MONEY_QUANT
        )
        position.quantity -= quantity
        if position.quantity == 0:
            position.average_price = Decimal("0")

    position.save()

    return PortfolioTransaction.objects.create(
        portfolio=portfolio,
        share=share,
        operation=operation,
        quantity=quantity,
        price=price,
        realized_pnl=realized_pnl,
    )
