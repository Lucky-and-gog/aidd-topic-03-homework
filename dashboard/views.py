from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError

from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, View, UpdateView

from .forms import PortfolioForm, ShareModelForm, TradeForm
from .models import Portfolio, Position, Share
from .services.portfolio import buy_shares, portfolio_totals, sell_shares
from .services.graph import get_graph
from django.contrib.auth.mixins import UserPassesTestMixin


class IsUserAuthenticatedMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated

    @staticmethod
    def handle_no_permission():
        return redirect("dashboard:index")


class ShareListView(ListView):
    """Список акций"""

    model = Share
    template_name = "dashboard/list.html"
    paginate_by = 100
    ordering = ["name"]


class ShareDetailView(View):
    @staticmethod
    def get(request, pk):
        share = get_object_or_404(Share, id=pk)

        return render(
            request,
            "dashboard/detail.html",
            {"plot_div": get_graph(share), "share": share},
        )


class ShareCreateView(IsUserAuthenticatedMixin, CreateView):
    """Добавление инструмента"""

    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareUpdateView(IsUserAuthenticatedMixin, UpdateView):
    """Редактирование инструмента"""

    model = Share
    template_name = "dashboard/create.html"
    form_class = ShareModelForm
    success_url = reverse_lazy("dashboard:index")


class ShareDeleteView(IsUserAuthenticatedMixin, DeleteView):
    """Удаление задачи"""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")
class PortfolioListView(LoginRequiredMixin, ListView):
    """Список портфелей текущего пользователя."""

    model = Portfolio
    template_name = "dashboard/portfolio_list.html"
    context_object_name = "portfolios"

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user).order_by("-created_at")


class PortfolioCreateView(LoginRequiredMixin, CreateView):
    """Создание нового портфеля."""

    model = Portfolio
    form_class = PortfolioForm
    template_name = "dashboard/portfolio_form.html"
    success_url = None

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("dashboard:portfolio_detail", kwargs={"pk": self.object.pk})


class PortfolioDetailView(LoginRequiredMixin, View):
    """Детальная информация о портфеле: позиции, стоимость, PnL, история."""

    @staticmethod
    def get(request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        totals = portfolio_totals(portfolio)
        positions = portfolio.positions.select_related("share").order_by("share__name")
        transactions = portfolio.transactions.select_related("share").order_by("-created_at")[:50]
        return render(
            request,
            "dashboard/portfolio_detail.html",
            {
                "portfolio": portfolio,
                "positions": positions,
                "transactions": transactions,
                "totals": totals,
            },
        )


class PortfolioDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление портфеля."""

    model = Portfolio
    template_name = "dashboard/portfolio_delete.html"
    success_url = reverse_lazy("dashboard:portfolio_list")

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)


class BuyShareView(LoginRequiredMixin, View):
    """Покупка акций в портфель."""

    @staticmethod
    def get(request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        form = TradeForm()
        return render(
            request,
            "dashboard/trade_form.html",
            {"portfolio": portfolio, "form": form, "operation": "buy", "title": "Покупка акций"},
        )

    @staticmethod
    def post(request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        form = TradeForm(request.POST)
        if form.is_valid():
            try:
                buy_shares(
                    portfolio,
                    form.cleaned_data["share"],
                    form.cleaned_data["quantity"],
                    form.cleaned_data["price"],
                )
                return redirect("dashboard:portfolio_detail", pk=portfolio.pk)
            except ValidationError as exc:
                form.add_error(None, exc.message)
        return render(
            request,
            "dashboard/trade_form.html",
            {"portfolio": portfolio, "form": form, "operation": "buy", "title": "Покупка акций"},
        )


class SellShareView(LoginRequiredMixin, View):
    """Продажа акций из портфеля."""

    @staticmethod
    def get(request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        form = TradeForm()
        return render(
            request,
            "dashboard/trade_form.html",
            {"portfolio": portfolio, "form": form, "operation": "sell", "title": "Продажа акций"},
        )

    @staticmethod
    def post(request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        form = TradeForm(request.POST)
        if form.is_valid():
            try:
                sell_shares(
                    portfolio,
                    form.cleaned_data["share"],
                    form.cleaned_data["quantity"],
                    form.cleaned_data["price"],
                )
                return redirect("dashboard:portfolio_detail", pk=portfolio.pk)
            except ValidationError as exc:
                form.add_error(None, exc.message)
        return render(
            request,
            "dashboard/trade_form.html",
            {"portfolio": portfolio, "form": form, "operation": "sell", "title": "Продажа акций"},
        )
