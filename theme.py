import streamlit as st
from plotly.graph_objs import Figure


LIGHT_COLORS = {
    "background": "#FFFFFF",
    "secondary": "#F0F2F6",
    "text": "#31333F",
    "muted": "#6B7280",
    "border": "#D1D5DB",
    "grid": "#E5E7EB",
}

DARK_COLORS = {
    "background": "#0E1117",
    "secondary": "#262730",
    "text": "#FAFAFA",
    "muted": "#B8C0CC",
    "border": "#3B4252",
    "grid": "#343B4A",
}


def inject_css():
    """Inject the app-wide CSS used by app.py and Streamlit pages."""
    st.markdown(
        '''<style>
        .main .block-container{padding-top:2rem;padding-bottom:2rem}
        [data-testid="metric-container"]{padding:1.1rem;border-radius:.5rem}
        h1,h2,h3,h4,h5,h6{font-weight:600}
        </style>''',
        unsafe_allow_html=True,
    )


def is_dark_theme():
    """Return the active Streamlit theme selected by the user."""
    try:
        return st.context.theme.type == "dark"
    except Exception:
        try:
            return st.get_option("theme.base") == "dark"
        except Exception:
            return False


def get_theme_colors():
    return DARK_COLORS if is_dark_theme() else LIGHT_COLORS


def theme_colors():
    return get_theme_colors()


def apply_plotly_theme(fig: Figure) -> Figure:
    """Apply the active Streamlit theme plus safe spacing to Plotly figures."""
    colors = get_theme_colors()

    fig.update_layout(
        paper_bgcolor=colors["background"],
        plot_bgcolor=colors["background"],
        font=dict(color=colors["text"]),
        title_font=dict(color=colors["text"]),
        margin=dict(l=70, r=115, t=80, b=65),
        legend=dict(
            font=dict(color=colors["text"]),
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            traceorder="normal",
        ),
    )

    try:
        fig.update_xaxes(
            title_font=dict(color=colors["text"]),
            tickfont=dict(color=colors["text"]),
            gridcolor=colors["grid"],
            zerolinecolor=colors["grid"],
            linecolor=colors["border"],
            automargin=True,
        )
        fig.update_yaxes(
            title_font=dict(color=colors["text"]),
            tickfont=dict(color=colors["text"]),
            gridcolor=colors["grid"],
            zerolinecolor=colors["grid"],
            linecolor=colors["border"],
            automargin=True,
        )
    except Exception:
        pass

    is_forecast_trajectory = False
    try:
        title_text = fig.layout.title.text if fig.layout.title else ""
        is_forecast_trajectory = bool(title_text and str(title_text).startswith("Export Trajectory"))
    except Exception:
        pass

    for trace in fig.data:
        if is_forecast_trajectory:
            try:
                if getattr(trace, "marker", None) is not None:
                    trace.marker.showscale = False
            except Exception:
                pass

        for attr in ("textfont", "insidetextfont", "outside_textfont"):
            try:
                current = getattr(trace, attr, None)
                if current is not None:
                    current_json = current.to_plotly_json() if hasattr(current, "to_plotly_json") else dict(current)
                    if "color" not in current_json:
                        current_json["color"] = colors["text"]
                    setattr(trace, attr, current_json)
            except Exception:
                pass

        for cb in (
            getattr(getattr(trace, "marker", None), "colorbar", None),
            getattr(trace, "colorbar", None),
        ):
            try:
                if cb is None:
                    continue
                if is_forecast_trajectory:
                    continue
                title_text = cb.title.text if cb.title and cb.title.text else ""
                cb.title = dict(text=title_text, font=dict(color=colors["text"]))
                cb.tickfont = dict(color=colors["text"], size=10)
                cb.outlinecolor = colors["border"]
                cb.nticks = 5
                cb.len = 0.72
                cb.x = 1.04
                cb.xanchor = "left"
                cb.y = 0.5
                cb.yanchor = "middle"
                cb.ticklabeloverflow = "hide past div"
            except Exception:
                pass

    # Plotly Express figures can use a shared layout.coloraxis colorbar.
    try:
        coloraxis = fig.layout.coloraxis
        if coloraxis and coloraxis.colorbar:
            if is_forecast_trajectory:
                coloraxis.showscale = False
            else:
                coloraxis.colorbar.tickfont = dict(color=colors["text"], size=10)
                coloraxis.colorbar.outlinecolor = colors["border"]
                coloraxis.colorbar.nticks = 5
                coloraxis.colorbar.len = 0.72
                coloraxis.colorbar.x = 1.04
                coloraxis.colorbar.xanchor = "left"
                coloraxis.colorbar.y = 0.5
                coloraxis.colorbar.yanchor = "middle"
    except Exception:
        pass

    for annotation in list(fig.layout.annotations) if fig.layout.annotations else []:
        try:
            existing_font = annotation.font.to_plotly_json() if annotation.font else {}
            if "color" not in existing_font:
                existing_font["color"] = colors["text"]
                annotation.font = existing_font
        except Exception:
            try:
                if not annotation.font or annotation.font.color is None:
                    annotation.font.color = colors["text"]
            except Exception:
                pass

    return fig



def render_chart(fig, key=None, height=None):
    """Render a Plotly chart through the single app-wide theme pipeline."""
    fig = apply_plotly_theme(fig)
    if height is not None:
        fig.update_layout(height=height)
    kwargs = {"use_container_width": True, "theme": None}
    if key is not None:
        kwargs["key"] = key
    st.plotly_chart(fig, **kwargs)


def make_line_figure(series_map, title="", yaxis_title="", height=420):
    """Create a consistent responsive line chart from named pandas Series."""
    import plotly.graph_objects as go
    fig = go.Figure()
    for name, series in series_map:
        clean = series.dropna()
        fig.add_trace(go.Scatter(
            x=clean.index,
            y=clean.values,
            mode="lines",
            name=name,
            hovertemplate="%{x}<br>%{y:,.2f}<extra>" + str(name) + "</extra>",
        ))
    fig.update_layout(title=title, yaxis_title=yaxis_title, height=height, hovermode="x unified")
    return apply_plotly_theme(fig)


def patch_streamlit_plotly_chart():
    """Apply our figure theme and disable Streamlit's second chart theme layer."""
    if getattr(st, "_trade_war_plotly_theme_patched", False):
        return

    original_plotly_chart = st.plotly_chart

    def themed_plotly_chart(figure_or_data, *args, **kwargs):
        if isinstance(figure_or_data, Figure):
            figure_or_data = apply_plotly_theme(figure_or_data)
            kwargs["theme"] = None
        return original_plotly_chart(figure_or_data, *args, **kwargs)

    st.plotly_chart = themed_plotly_chart
    st._trade_war_plotly_theme_patched = True
