from decimal import Decimal

from django.core.exceptions import ValidationError

from dashboard.models import Portfolio, Position, PortfolioTransaction, Share


def _to_decimal(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def buy_shares(portfolio, share, quantity, price):
    quantity = _to_decimal(quantity)
    price = _to_decimal(price)
    if quantity <= 0:
        raise ValidationError("Количество должно быть больше нуля.")
    if price < 0:
        raise ValidationError("Цена не может быть отрицательной.")

    position, _ = Position.objects.get_or_create(
        portfolio=portfolio, share=share, defaults={"quantity": Decimal("0"), "average_price": Decimal("0")}
    )
    old_qty = position.quantity
    old_avg = position.average_price
    new_qty = old_qty + quantity
    if new_qty > 0:
        position.average_price = (old_qty * old_avg + quantity * price) / new_qty
    position.quantity = new_qty
    position.save()

    PortfolioTransaction.objects.create(
        portfolio=portfolio,
        share=share,
        operation=PortfolioTransaction.OPERATION_BUY,
        quantity=quantity,
        price=price,
        realized_pnl=Decimal("0"),
    )
    return position


def sell_shares(portfolio, share, quantity, price):
    quantity = _to_decimal(quantity)
    price = _to_decimal(price)
    if quantity <= 0:
        raise ValidationError("Количество должно быть больше нуля.")

    try:
        position = Position.objects.get(portfolio=portfolio, share=share)
    except Position.DoesNotExist:
        raise ValidationError("Позиция по данной акции отсутствует.")

    if quantity > position.quantity:
        raise ValidationError("Недостаточно акций для продажи.")

    avg_price = position.average_price
    realized_pnl = (price - avg_price) * quantity

    position.quantity = position.quantity - quantity
    position.save()

    PortfolioTransaction.objects.create(
        portfolio=portfolio,
        share=share,
        operation=PortfolioTransaction.OPERATION_SELL,
        quantity=quantity,
        price=price,
        realized_pnl=realized_pnl,
    )
    return position


def portfolio_totals(portfolio):
    market_value = Decimal("0")
    cost_basis = Decimal("0")
    for position in portfolio.positions.select_related("share"):
        market_value += position.market_value
        cost_basis += position.cost_basis
    unrealized_pnl = market_value - cost_basis
    realized_pnl = sum(
        (t.realized_pnl for t in portfolio.transactions.all()), Decimal("0")
    )
    return {
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "total_pnl": unrealized_pnl + realized_pnl,
    }