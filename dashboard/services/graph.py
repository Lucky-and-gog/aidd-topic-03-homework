# from tinkoff.invest import CandleInterval, Client
# from tinkoff.invest.utils import now

from plotly.graph_objs import Scatter
from plotly.offline import plot

from config.settings import TINKOFF_TOKEN


def get_graph(share):
    """Заглушка: возвращает пустой график без обращения к Tinkoff API."""
    plot_div = plot(
        [Scatter(x=[], y=[], mode="lines", name="test")],
        output_type="div",
        show_link=False,
        link_text="",
    )
    return plot_div
