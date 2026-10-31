from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from dashboard.models import Portfolio, PortfolioTransaction, Position, Share
from dashboard.services.portfolio import execute_transaction

User = get_user_model()


class PortfolioServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="password123",
        )
        self.portfolio = Portfolio.objects.create(user=self.user, name="Тестовый")
        self.share = Share.objects.create(
            figi="FIGI-TEST",
            isin="ISIN-TEST",
            name="Test Share",
            ticker="TST",
            currency="rub",
            uid="UID-TEST",
            last_price=300.0,
        )

    def buy(self, quantity, price):
        return execute_transaction(
            self.portfolio,
            self.share,
            PortfolioTransaction.Operation.BUY,
            quantity,
            price,
        )

    def sell(self, quantity, price):
        return execute_transaction(
            self.portfolio,
            self.share,
            PortfolioTransaction.Operation.SELL,
            quantity,
            price,
        )

    def test_buy_calculates_average_price(self):
        self.buy(10, 100)
        self.buy(10, 200)

        position = Position.objects.get(
            portfolio=self.portfolio, share=self.share
        )
        self.assertEqual(position.quantity, Decimal("20"))
        self.assertEqual(position.average_price, Decimal("150.0000"))

    def test_sell_calculates_realized_profit(self):
        self.buy(10, 100)
        transaction = self.sell(5, 250)

        position = Position.objects.get(
            portfolio=self.portfolio, share=self.share
        )
        self.assertEqual(position.quantity, Decimal("5"))
        self.assertEqual(position.average_price, Decimal("100.0000"))
        self.assertEqual(transaction.realized_pnl, Decimal("750.0000"))

    def test_sell_more_than_available_raises(self):
        self.buy(1, 100)

        with self.assertRaises(ValidationError):
            self.sell(2, 100)

    def test_portfolio_totals(self):
        self.buy(10, 100)
        self.buy(10, 200)
        self.sell(5, 250)

        self.assertEqual(self.portfolio.invested_value, Decimal("2250"))
        self.assertEqual(self.portfolio.current_value, Decimal("4500"))
        self.assertEqual(self.portfolio.unrealized_pnl, Decimal("2250"))
        self.assertEqual(self.portfolio.realized_pnl, Decimal("500.0000"))
        self.assertEqual(self.portfolio.total_pnl, Decimal("2750.0000"))


class PortfolioViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="password123",
        )
        self.other = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="password123",
        )
        self.portfolio = Portfolio.objects.create(user=self.user, name="Мой")
        self.other_portfolio = Portfolio.objects.create(
            user=self.other, name="Чужой"
        )
        self.share = Share.objects.create(
            figi="FIGI-VIEW",
            isin="ISIN-VIEW",
            name="View Share",
            ticker="VW",
            currency="rub",
            uid="UID-VIEW",
            last_price=150.0,
        )
        self.client.force_login(self.user)

    def test_portfolio_list_and_detail(self):
        response = self.client.get(reverse("dashboard:portfolio_list"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse("dashboard:portfolio_detail", args=[self.portfolio.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_other_user_portfolio_is_not_accessible(self):
        response = self.client.get(
            reverse("dashboard:portfolio_detail", args=[self.other_portfolio.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_create_transaction_updates_position(self):
        response = self.client.post(
            reverse("dashboard:transaction_create", args=[self.portfolio.pk]),
            {
                "share": self.share.pk,
                "operation": PortfolioTransaction.Operation.BUY,
                "quantity": "10",
                "price": "100",
            },
        )
        self.assertEqual(response.status_code, 302)

        position = Position.objects.get(
            portfolio=self.portfolio, share=self.share
        )
        self.assertEqual(position.quantity, Decimal("10"))
        self.assertEqual(position.average_price, Decimal("100.0000"))
