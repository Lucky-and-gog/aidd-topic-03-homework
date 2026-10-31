from plotly.graph_objs import Scatter
from plotly.offline import plot


def get_graph(share):
    """Заглушка вместо Tinkoff Invest API: возвращает пустой Plotly-график."""
    plot_div = plot(
        [
            Scatter(
                x=[],
                y=[],
                mode="lines",
                name=share.ticker,
                opacity=0.8,
                marker_color="red",
            )
        ],
        output_type="div",
        show_link=False,
        link_text="",
    )
    return plot_div
