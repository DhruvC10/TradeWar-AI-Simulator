import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm
from historical_analysis import (
    sample_data, prepare, validate_data, render_dataset_metrics, make_plot,
    fit_ols, forecast_arima, elasticity_prediction, did_analysis, hide_chart_colorbars,
)
from theme import inject_css, apply_plotly_theme, render_chart
from components.learning import render_learning_header, render_page_learning

inject_css()
st.title("🔬 Historical Data & Economics Lab")
st.markdown("Upload or enter real historical observations, test economic relationships, forecast exports, and generate research-ready results — without leaving the app.")
st.info("**Research principle:** statistical/economic models generate the quantitative result. AI can be added later as an explanation layer; it should not be treated as the source of the underlying coefficient or prediction.")

render_learning_header("Historical data & economics", "Learn the method first, then use your own observations to test an economic relationship.")
render_page_learning("historical")

with st.sidebar:
    st.header("📥 Data source")
    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    if st.button("Use built-in sample dataset", use_container_width=True):
        st.session_state["econ_df"] = sample_data()
    st.caption("Required: year, exports_bn_usd, tariff_pct. Optional: gdp_bn_usd, exchange_rate, inflation_pct, imports_bn_usd, trade_volume.")

if uploaded is not None:
    try:
        raw = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
        st.session_state["econ_df"] = prepare(raw)
    except Exception as exc:
        st.error(f"Could not read the file: {exc}")

if "econ_df" not in st.session_state:
    st.session_state["econ_df"] = sample_data()

df = prepare(st.session_state["econ_df"])

st.subheader("1. Historical dataset")
st.caption("Edit values directly, add observations, or paste a prepared dataset. Changes are used immediately by the analyses below.")
edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="historical_editor")
st.session_state["econ_df"] = prepare(edited)
df = prepare(edited)

year_range = []
if "year" in df.columns and len(df):
    years = pd.to_numeric(df["year"], errors="coerce").dropna()
    if len(years):
        year_range = [int(years.min()), int(years.max())]

latest_exports = None
if {"year", "exports_bn_usd"}.issubset(df.columns) and len(df):
    ordered = df.copy()
    ordered["year"] = pd.to_numeric(ordered["year"], errors="coerce")
    ordered = ordered.dropna(subset=["year"]).sort_values("year")
    if len(ordered):
        latest_exports = float(ordered.iloc[-1]["exports_bn_usd"])

issues = validate_data(df)
if issues:
    for issue in issues:
        st.warning(issue)
else:
    st.success("Dataset validation passed: core fields are present and numeric.")
render_dataset_metrics(df)

c1, c2 = st.columns(2)
with c1:
    st.download_button("⬇️ Download cleaned CSV", df.to_csv(index=False).encode("utf-8"), "historical_trade_data.csv", "text/csv", use_container_width=True)
with c2:
    st.download_button("⬇️ Download sample template", sample_data().to_csv(index=False).encode("utf-8"), "trade_analysis_template.csv", "text/csv", use_container_width=True)

render_chart(make_plot(df), key="historical_primary_chart")

st.divider()
st.subheader("2. Descriptive statistics")
st.dataframe(df.describe(include="all").T, use_container_width=True)
if len(df) >= 3:
    numeric = df.select_dtypes(include=np.number)
    corr = numeric.corr()
    correlation_fig = px.imshow(corr, text_auto=False, aspect="auto", title="Correlation matrix", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)

    # Choose annotation text from the actual heatmap luminance, rather than
    # from the sign of the correlation. This keeps text readable on both very
    # light and very dark cells in either app theme.
    for row_idx, row_name in enumerate(corr.index):
        for col_idx, col_name in enumerate(corr.columns):
            value = float(corr.iloc[row_idx, col_idx])
            normalized = (value + 1.0) / 2.0
            # RdBu_r transitions from dark blue -> light -> dark red.
            # Approximate the rendered background luminance so the annotation
            # always gets the contrasting text color.
            if normalized < 0.5:
                t = normalized / 0.5
                r = 5 + (247 - 5) * t
                g = 48 + (247 - 48) * t
                b = 97 + (247 - 97) * t
            else:
                t = (normalized - 0.5) / 0.5
                r = 247 + (103 - 247) * t
                g = 247 + (0 - 247) * t
                b = 247 + (31 - 247) * t
            luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
            text_color = "#111827" if luminance > 0.58 else "#FFFFFF"
            correlation_fig.add_annotation(
                x=col_idx,
                y=row_idx,
                text=f"{value:.6f}",
                showarrow=False,
                font=dict(color=text_color, size=14),
                xanchor="center",
                yanchor="middle",
            )

    correlation_fig.update_layout(
        margin=dict(l=80, r=80, t=75, b=70),
        coloraxis_showscale=False,
    )
    render_chart(correlation_fig, key="historical_correlation")

st.divider()
st.subheader("3. Econometric model")
st.markdown("Estimate the relationship between exports and tariff rates while optionally controlling for macroeconomic variables.")
available = [c for c in ["tariff_pct", "gdp_bn_usd", "exchange_rate", "inflation_pct", "imports_bn_usd", "trade_volume"] if c in df.columns]
predictors = st.multiselect("Independent variables", available, default=["tariff_pct"] if "tariff_pct" in available else available[:1])
if predictors:
    try:
        model, model_data = fit_ols(df, predictors)
        st.markdown("### Estimated equation")
        terms = [f"{model.params['const']:.3f}"] + [f"({model.params[p]:+.4f}) × {p}" for p in predictors]
        st.code("exports_bn_usd = " + " ".join(terms))
        a, b, c, d = st.columns(4)
        a.metric("R²", f"{model.rsquared:.3f}")
        b.metric("Adjusted R²", f"{model.rsquared_adj:.3f}")
        c.metric("Observations", int(model.nobs))
        d.metric("Tariff coefficient", f"{model.params.get('tariff_pct', np.nan):.4f}")
        st.markdown("**Interpretation:** the tariff coefficient estimates the expected change in exports ($B) associated with a one-percentage-point tariff change, holding the selected controls constant.")
        st.dataframe(pd.DataFrame({"coefficient": model.params, "std_error": model.bse, "p_value": model.pvalues, "ci_low": model.conf_int()[0], "ci_high": model.conf_int()[1]}), use_container_width=True)
        with st.expander("Full statistical summary"):
            st.text(model.summary().as_text())
        fitted = model.predict(sm.add_constant(model_data[predictors], has_constant="add"))
        pred_df = model_data[["exports_bn_usd"]].copy()
        pred_df["predicted"] = fitted.values
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=pred_df["exports_bn_usd"], mode="lines+markers", name="Actual"))
        fig.add_trace(go.Scatter(y=pred_df["predicted"], mode="lines+markers", name="OLS predicted"))
        fig.update_layout(title="Actual vs OLS predicted exports", xaxis_title="Observation", yaxis_title="Exports ($B)", margin=dict(l=70, r=70, t=75, b=65), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), coloraxis_showscale=False, coloraxis=dict(showscale=False), coloraxis2=dict(showscale=False), coloraxis3=dict(showscale=False))
        fig = hide_chart_colorbars(fig)
        render_chart(fig, key="historical_model_chart")
    except Exception as exc:
        st.error(f"Model could not be estimated: {exc}")
else:
    st.warning("Select at least one independent variable.")

st.divider()
st.subheader("4. Economic theory / tariff counterfactual")
st.markdown("Use a transparent elasticity model alongside the historical regression. This makes the mechanism explicit rather than treating the prediction as a black-box AI output.")
last_exports = float(df.sort_values("year").iloc[-1]["exports_bn_usd"]) if len(df) else 0
c1, c2, c3 = st.columns(3)
with c1: tariff_shock = st.number_input("Counterfactual tariff change (%)", -90.0, 200.0, 10.0, 1.0)
with c2: elasticity = st.number_input("Demand/trade elasticity", -5.0, 5.0, -0.7, 0.1)
with c3: st.metric("Latest observed exports", f"${last_exports:.2f}B")
predicted = elasticity_prediction(last_exports, tariff_shock, elasticity)
pct_change = (predicted / last_exports - 1) * 100 if last_exports else 0
st.success(f"**Elasticity counterfactual:** ${last_exports:.2f}B → **${predicted:.2f}B** ({pct_change:+.2f}%).")
st.latex(r"\frac{\Delta Q}{Q}=\epsilon\frac{\Delta P}{P}")
st.caption("This is a partial-equilibrium first-order approximation. It does not automatically capture retaliation, investment relocation, exchange-rate responses, political effects, or general-equilibrium feedbacks.")

st.divider()
st.subheader("5. Forecasting")
steps = st.slider("Forecast horizon", 1, 10, 5)
try:
    _, mean, ci = forecast_arima(df, steps)
    future_years = np.arange(int(df.year.max()) + 1, int(df.year.max()) + steps + 1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.year, y=df.exports_bn_usd, mode="lines+markers", name="Historical"))
    fig.add_trace(go.Scatter(x=future_years, y=mean, mode="lines+markers", name="ARIMA forecast"))
    fig.add_trace(go.Scatter(x=future_years, y=ci.iloc[:, 1], mode="lines", line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=future_years, y=ci.iloc[:, 0], mode="lines", fill="tonexty", line=dict(width=0), name="95% interval"))
    fig.update_layout(title="Export forecast", xaxis_title="Year", yaxis_title="Exports ($B)", margin=dict(l=70, r=70, t=75, b=65), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), coloraxis_showscale=False, coloraxis=dict(showscale=False), coloraxis2=dict(showscale=False), coloraxis3=dict(showscale=False))
    fig = hide_chart_colorbars(fig)
    render_chart(fig, key="historical_forecast_chart")
    st.dataframe(pd.DataFrame({"year": future_years, "forecast_exports_bn_usd": mean.values, "lower_95": ci.iloc[:,0].values, "upper_95": ci.iloc[:,1].values}), use_container_width=True)
except Exception as exc:
    st.warning(f"ARIMA forecast unavailable: {exc}")

st.divider()
st.subheader("6. Trade-war event / Difference-in-Differences")
st.markdown("For a real intervention analysis, provide a defensible treatment/control definition. The simple mode below is a teaching implementation; it classifies high-tariff observations as treated and should not be presented as causal proof without a proper control group and parallel-trends checks.")
start_year = st.number_input("Policy/intervention start year", int(df.year.min()) if len(df) else 2000, int(df.year.max()) if len(df) else 2025, min(2018, int(df.year.max())) if len(df) else 2018)
if st.button("Run DiD analysis", use_container_width=True):
    try:
        did_model, _ = did_analysis(df, int(start_year))
        st.metric("Estimated DiD effect", f"{did_model.params['treated_post']:.3f} $B", help="Interaction coefficient in this simplified single-series teaching setup.")
        st.dataframe(pd.DataFrame({"coefficient": did_model.params, "std_error": did_model.bse, "p_value": did_model.pvalues, "ci_low": did_model.conf_int()[0], "ci_high": did_model.conf_int()[1]}), use_container_width=True)
        st.warning("For publication-quality causal inference, use panel data with a clearly defined untreated control group and parallel-trends checks.")
    except Exception as exc:
        st.error(f"DiD could not be estimated: {exc}")

st.divider()
st.subheader("7. Research-ready output")
report = f"""TradeWar AI Simulator — Historical Economics Analysis\n\nDataset: {len(df)} observations, {int(df.year.min()) if len(df) else 'N/A'}–{int(df.year.max()) if len(df) else 'N/A'}\nAverage tariff: {df.tariff_pct.mean():.3f}%\nAverage exports: ${df.exports_bn_usd.mean():.3f}B\n\nEconomic model\nTariff shock: {tariff_shock:+.2f}%\nElasticity: {elasticity:+.2f}\nCounterfactual exports: ${predicted:.3f}B\n\nMethodological note\nResults are model-based estimates. Historical observational data do not by themselves establish causality. Model assumptions, omitted variables, measurement error, and structural breaks can affect results.\n"""
st.download_button("📄 Download research analysis summary", report, "tradewar_research_summary.txt", "text/plain", use_container_width=True)
