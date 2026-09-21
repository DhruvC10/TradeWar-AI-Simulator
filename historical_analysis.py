import io
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

REQUIRED_CORE = ["year", "exports_bn_usd", "tariff_pct"]
OPTIONAL_COLUMNS = ["imports_bn_usd", "gdp_bn_usd", "exchange_rate", "inflation_pct", "trade_volume"]


def sample_data():
    years = np.arange(1995, 2026)
    tariff = np.array([4.1,4.0,3.9,4.0,3.8,4.2,3.7,3.6,3.5,3.6,3.5,3.4,3.3,3.2,3.1,3.0,3.2,3.1,3.0,3.1,3.2,3.3,3.4,12.8,21.0,19.3,18.7,17.9,16.5,15.2,14.8])
    exports = [45.1]
    for i in range(1, len(years)):
        growth = 0.065 - max(tariff[i] - 4, 0) * 0.012
        exports.append(exports[-1] * (1 + growth))
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "year": years,
        "exports_bn_usd": np.round(np.array(exports) * rng.uniform(.96, 1.04, len(years)), 2),
        "tariff_pct": tariff,
        "gdp_bn_usd": np.round(np.linspace(7600, 30000, len(years)), 1),
        "exchange_rate": np.round(np.linspace(7.6, 7.1, len(years)), 3),
        "inflation_pct": np.round(rng.uniform(1.0, 5.0, len(years),), 2),
    })


def normalize_columns(df):
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in out.columns]
    aliases = {
        "date": "year", "yr": "year", "exports": "exports_bn_usd", "export_value": "exports_bn_usd",
        "export_value_bn_usd": "exports_bn_usd", "tariff": "tariff_pct", "tariff_rate": "tariff_pct",
        "gdp": "gdp_bn_usd", "fx": "exchange_rate", "exchange": "exchange_rate", "inflation": "inflation_pct"
    }
    out = out.rename(columns={c: aliases.get(c, c) for c in out.columns})
    if "year" in out:
        out["year"] = pd.to_numeric(out["year"], errors="coerce")
    return out


def validate_data(df):
    issues = []
    missing = [c for c in REQUIRED_CORE if c not in df.columns]
    if missing:
        issues.append(f"Missing required columns: {', '.join(missing)}")
        return issues
    for c in REQUIRED_CORE + [x for x in OPTIONAL_COLUMNS if x in df.columns]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if df[REQUIRED_CORE].isna().any().any():
        issues.append("Required columns contain missing or non-numeric values.")
    if df["year"].duplicated().any():
        issues.append("Duplicate years detected; aggregate or remove duplicates before time-series analysis.")
    if (df["exports_bn_usd"] < 0).any():
        issues.append("Negative export values detected.")
    if (df["tariff_pct"] < 0).any():
        issues.append("Negative tariff values detected; verify whether these represent subsidies or tariff reductions.")
    if len(df) < 8:
        issues.append("Fewer than 8 observations: regression/forecast estimates may be unstable.")
    return issues


def prepare(df):
    df = normalize_columns(df)
    for c in REQUIRED_CORE + [x for x in OPTIONAL_COLUMNS if x in df.columns]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_values("year").reset_index(drop=True)


def fit_ols(df, predictors):
    cols = ["exports_bn_usd"] + predictors
    data = df[cols].dropna()
    if len(data) < max(8, len(predictors) + 3):
        raise ValueError("Not enough complete observations for this model.")
    X = sm.add_constant(data[predictors], has_constant="add")
    model = sm.OLS(data["exports_bn_usd"], X).fit()
    return model, data


def forecast_arima(df, steps=5):
    series = df.dropna(subset=["exports_bn_usd"]).sort_values("year")["exports_bn_usd"].astype(float)
    if len(series) < 8:
        raise ValueError("At least 8 observations are recommended for ARIMA forecasting.")
    model = ARIMA(series, order=(1, 1, 1)).fit()
    forecast = model.get_forecast(steps=steps)
    mean = forecast.predicted_mean
    ci = forecast.conf_int()
    return model, mean, ci


def elasticity_prediction(base_exports, tariff_change_pct, elasticity):
    return max(0.0, base_exports * (1 + elasticity * tariff_change_pct / 100.0))


def model_metrics(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    mape = float(np.mean(np.abs((actual - predicted) / np.where(actual == 0, np.nan, actual))) * 100)
    return {"MAE": float(mean_absolute_error(actual, predicted)), "RMSE": rmse, "MAPE": mape, "R²": float(r2_score(actual, predicted))}



def hide_chart_colorbars(fig):
    """Ensure Historical Data Lab charts never render Plotly colorbars."""
    fig.update_layout(coloraxis_showscale=False)
    try:
        fig.layout.coloraxis.showscale = False
    except Exception:
        pass
    for trace in fig.data:
        try:
            if getattr(trace, "marker", None) is not None:
                trace.marker.showscale = False
                trace.marker.colorbar = None
        except Exception:
            pass
        try:
            trace.showscale = False
            trace.colorbar = None
        except Exception:
            pass
    return fig

def make_plot(df, title="Historical exports and tariffs"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.year, y=df.exports_bn_usd, mode="lines+markers", name="Exports ($B)",
        yaxis="y", hovertemplate="Year: %{x}<br>Exports: $%{y:.2f}B<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=df.year, y=df.tariff_pct, mode="lines+markers", name="Tariff (%)",
        yaxis="y2", hovertemplate="Year: %{x}<br>Tariff: %{y:.2f}%<extra></extra>"
    ))
    fig.update_layout(
        title=title,
        xaxis=dict(title="Year", automargin=True, tickmode="auto", nticks=8),
        yaxis=dict(title="Exports ($B)", automargin=True),
        yaxis2=dict(title="Tariff (%)", overlaying="y", side="right", automargin=True),
        hovermode="x unified",
        margin=dict(l=70, r=90, t=75, b=65),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        coloraxis_showscale=False,
    )
    return hide_chart_colorbars(fig)


def style_historical_chart(fig, legend=True):
    """Keep charts in Historical Data Lab readable without changing data or series styling."""
    layout = dict(
        margin=dict(l=70, r=70, t=75, b=65),
        hovermode="x unified",
        coloraxis_showscale=False,
    )
    if legend:
        layout["legend"] = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    fig.update_layout(**layout)
    for axis in ("xaxis", "yaxis", "yaxis2"):
        if axis in fig.layout:
            getattr(fig.layout, axis).automargin = True
    return fig


def did_analysis(df, treatment_start, treatment_col="tariff_pct"):
    d = df.copy().sort_values("year")
    median = d[treatment_col].median()
    d["treated"] = (d[treatment_col] >= median).astype(int)
    d["post"] = (d["year"] >= treatment_start).astype(int)
    d["treated_post"] = d["treated"] * d["post"]
    d = d.dropna(subset=["exports_bn_usd", "treated", "post"])
    X = sm.add_constant(d[["treated", "post", "treated_post"]], has_constant="add")
    model = sm.OLS(d["exports_bn_usd"], X).fit()
    return model, d


def render_dataset_metrics(df):
    cols = st.columns(4)
    cols[0].metric("Observations", len(df))
    cols[1].metric("Years", f"{int(df.year.min())}–{int(df.year.max())}" if len(df) else "—")
    cols[2].metric("Avg. tariff", f"{df.tariff_pct.mean():.2f}%")
    cols[3].metric("Avg. exports", f"${df.exports_bn_usd.mean():.2f}B")
