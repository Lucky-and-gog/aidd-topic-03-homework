from decimal import Decimal

from django import forms

from .models import Portfolio, PortfolioTransaction, Position, Share
from .services.portfolio import execute_transaction

CONTROL_CLASS = "form-control"


class ShareModelForm(forms.ModelForm):
    """Инструмент"""

    class Meta:
        model = Share
        fields = "__all__"


class PortfolioForm(forms.ModelForm):
    """Создание портфеля."""

    class Meta:
        model = Portfolio
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": CONTROL_CLASS,
                    "placeholder": "Например, Мой портфель",
                }
            )
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = self.cleaned_data["name"]
        if self.user and Portfolio.objects.filter(
            user=self.user, name=name
        ).exists():
            raise forms.ValidationError(
                "Портфель с таким названием уже существует"
            )
        return name


class TransactionForm(forms.Form):
    """Операция покупки или продажи акции."""

    share = forms.ModelChoiceField(
        queryset=Share.objects.order_by("name"),
        label="Акция",
        widget=forms.Select(attrs={"class": CONTROL_CLASS}),
    )
    operation = forms.ChoiceField(
        choices=PortfolioTransaction.Operation.choices,
        label="Операция",
        widget=forms.Select(attrs={"class": CONTROL_CLASS}),
    )
    quantity = forms.DecimalField(
        label="Количество",
        min_value=Decimal("0.000001"),
        max_digits=20,
        decimal_places=6,
        widget=forms.NumberInput(
            attrs={"class": CONTROL_CLASS, "step": "0.000001"}
        ),
    )
    price = forms.DecimalField(
        label="Цена за единицу",
        min_value=Decimal("0.0001"),
        max_digits=20,
        decimal_places=4,
        widget=forms.NumberInput(
            attrs={"class": CONTROL_CLASS, "step": "0.0001"}
        ),
    )

    def __init__(self, *args, portfolio=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.portfolio = portfolio

    def clean(self):
        cleaned_data = super().clean()
        operation = cleaned_data.get("operation")
        share = cleaned_data.get("share")
        quantity = cleaned_data.get("quantity")

        if (
            operation == PortfolioTransaction.Operation.SELL
            and share
            and quantity is not None
            and self.portfolio
        ):
            position = Position.objects.filter(
                portfolio=self.portfolio, share=share
            ).first()
            available = position.quantity if position else Decimal("0")
            if quantity > available:
                self.add_error(
                    "quantity",
                    f"Недостаточно акций для продажи: доступно {available}",
                )

        return cleaned_data

    def save(self):
        return execute_transaction(
            portfolio=self.portfolio,
            share=self.cleaned_data["share"],
            operation=self.cleaned_data["operation"],
            quantity=self.cleaned_data["quantity"],
            price=self.cleaned_data["price"],
        )
