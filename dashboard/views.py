from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from .forms import PortfolioForm, ShareModelForm, TransactionForm
from .models import Portfolio, Share
from .services.graph import get_graph


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
    """Удаление инструмента"""

    model = Share
    template_name = "dashboard/delete.html"
    success_url = reverse_lazy("dashboard:index")


class PortfolioListView(LoginRequiredMixin, ListView):
    """Список портфелей текущего пользователя."""

    model = Portfolio
    template_name = "dashboard/portfolio_list.html"
    context_object_name = "portfolios"

    def get_queryset(self):
        return (
            Portfolio.objects.filter(user=self.request.user)
            .prefetch_related("positions__share", "transactions")
        )


class PortfolioDetailView(LoginRequiredMixin, DetailView):
    """Портфель: позиции, стоимость, прибыль и история операций."""

    model = Portfolio
    template_name = "dashboard/portfolio_detail.html"
    context_object_name = "portfolio"

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user).prefetch_related(
            "positions__share", "transactions__share"
        )


class PortfolioCreateView(LoginRequiredMixin, CreateView):
    """Создание персонального портфеля."""

    model = Portfolio
    form_class = PortfolioForm
    template_name = "dashboard/portfolio_create.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("dashboard:portfolio_detail", kwargs={"pk": self.object.pk})


class PortfolioDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление портфеля."""

    model = Portfolio
    template_name = "dashboard/portfolio_confirm_delete.html"
    success_url = reverse_lazy("dashboard:portfolio_list")

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)


class TransactionCreateView(LoginRequiredMixin, View):
    """Добавление операции покупки или продажи в портфель."""

    template_name = "dashboard/transaction_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.portfolio = get_object_or_404(
            Portfolio, pk=kwargs["pk"], user=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = TransactionForm(portfolio=self.portfolio)
        return render(
            request,
            self.template_name,
            {"form": form, "portfolio": self.portfolio},
        )

    def post(self, request, *args, **kwargs):
        form = TransactionForm(request.POST, portfolio=self.portfolio)
        if form.is_valid():
            form.save()
            return redirect("dashboard:portfolio_detail", pk=self.portfolio.pk)
        return render(
            request,
            self.template_name,
            {"form": form, "portfolio": self.portfolio},
        )
