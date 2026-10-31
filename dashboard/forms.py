from django import forms

from .models import Share


class ShareModelForm(forms.ModelForm):
    """Инструмент"""

    class Meta:
        model = Share
        fields = "__all__"

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import Portfolio, Share


class PortfolioForm(forms.ModelForm):
    """Форма создания/редактирования портфеля."""

    class Meta:
        model = Portfolio
        fields = ["name"]


class TradeForm(forms.Form):
    """Форма покупки/продажи акций в портфеле."""

    share = forms.ModelChoiceField(
        queryset=Share.objects.all().order_by("name"),
        label="Акция",
    )
    quantity = forms.DecimalField(
        max_digits=18,
        decimal_places=4,
        min_value=Decimal("0.0001"),
        label="Количество",
    )
    price = forms.DecimalField(
        max_digits=18,
        decimal_places=4,
        required=False,
        min_value=Decimal("0"),
        label="Цена за единицу",
        help_text="Если не указана, используется текущая цена акции.",
    )

    def clean(self):
        cleaned_data = super().clean()
        share = cleaned_data.get("share")
        price = cleaned_data.get("price")
        if share is not None and price is None:
            if share.last_price is not None:
                cleaned_data["price"] = Decimal(str(share.last_price))
            else:
                raise ValidationError("Укажите цену: у акции нет текущей цены.")
        return cleaned_data
