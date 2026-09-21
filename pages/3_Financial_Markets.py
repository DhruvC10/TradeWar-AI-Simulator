import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils import COUNTRY_PROFILES, inject_css
from theme import apply_plotly_theme, render_chart, make_line_figure
from components.learning import render_learning_header, render_page_learning
from market_data import MARKETS, download_history, summarize, live_timestamp

inject_css()
st.title("💹 Financial Markets")
st.caption("Live observed market data is kept separate from modelled trade-policy scenarios.")
st.caption(f"Market refresh: {live_timestamp()} · Yahoo Finance is used for supported markets; Bangladesh DSE data uses the DSE adapter. Availability can vary by exchange/provider.")

country = st.sidebar.selectbox("Country / market", list(MARKETS), key="financial_country")
options = MARKETS[country]
labels = {f"{name} ({ticker})": (name, ticker, kind) for name, ticker, kind in options}
selected = st.sidebar.multiselect("Markets to compare", list(labels), default=list(labels)[:2], key="financial_markets")
period = st.sidebar.selectbox("History", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3, key="financial_period")

render_learning_header("Financial markets", "Learn the market concepts behind the live data before interpreting a chart.")
render_page_learning("financial")
rows = []
for label in selected:
    name, ticker, kind = labels[label]
    result = summarize(ticker, name)
    if result:
        rows.append({"Market": name, "Ticker": ticker, "Type": kind, "Latest": round(result["latest"], 2), "Daily %": round(result["daily_pct"], 2), "1Y %": round(result["period_pct"], 2), "Volume": result["volume"]})
    else:
        st.warning(f"No live data returned for {name} ({ticker}).")

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    fig = go.Figure()
    for label in selected:
        name, ticker, _ = labels[label]
        data = download_history(ticker, period)
        if not data.empty and "Close" in data:
            close = pd.to_numeric(data["Close"], errors="coerce").dropna()
            if not close.empty:
                fig.add_trace(go.Scatter(x=close.index, y=close / close.iloc[0] * 100, mode="lines", name=name))
    fig = apply_plotly_theme(fig.update_layout(title=f"Live market performance — {country}", yaxis_title="Indexed performance (start = 100)", height=420))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select one or more markets to load live data.")

st.divider()
st.subheader("🔎 Discover any listed instrument")
search = st.text_input("Search by company or ticker", placeholder="Reliance, Tata, Apple, Nvidia, AAPL, RELIANCE.NS")
if search.strip():
    from market_data import search_ticker
    results = search_ticker(search)
    if results.empty:
        st.warning("No Yahoo Finance instruments were found. Try a company name or exchange-qualified ticker.")
    else:
        st.dataframe(results, use_container_width=True, hide_index=True)
        chosen = st.selectbox("Load instrument", results["symbol"].tolist())
        data = download_history(chosen, period)
        if not data.empty and "Close" in data:
            close = pd.to_numeric(data["Close"], errors="coerce").dropna()
            if not close.empty:
                latest = float(close.iloc[-1]); previous = float(close.iloc[-2]) if len(close) > 1 else latest
                a, b, c = st.columns(3)
                a.metric("Latest", f"{latest:,.2f}")
                b.metric("Daily change", f"{(latest / previous - 1) * 100:+.2f}%")
                c.metric("Period change", f"{(latest / float(close.iloc[0]) - 1) * 100:+.2f}%")
                render_chart(make_line_figure([("Price", close)], title=f"{chosen} price history", yaxis_title="Price"), key="financial_custom_instrument")

st.divider()
st.subheader("📈 Live market vs. policy scenario")
scenario_ticker = options[0][1] if options else ""
live = summarize(scenario_ticker, options[0][0] if options else country)
if live:
    st.metric("Current live market level", f"{live['latest']:,.2f}", f"{live['daily_pct']:+.2f}% today")
    event = st.selectbox("Scenario shock", ["Tariff increase", "Tariff reduction", "Supply-chain disruption", "No shock"])
    intensity = st.slider("Shock intensity (%)", 0, 50, 20, 5)
    sensitivity = {"Tariff increase": -0.40, "Tariff reduction": 0.30, "Supply-chain disruption": -0.50, "No shock": 0.0}[event]
    model_return = sensitivity * intensity
    st.metric("Modelled scenario impact", f"{model_return:+.1f}%", help="Transparent scenario assumption applied to the current live level. It is not a live forecast or investment recommendation.")
    st.info(f"Starting from the live {options[0][0]} level of {live['latest']:,.2f}, the scenario applies a {model_return:+.1f}% model shock. The live series above remains unchanged.")
else:
    st.info("The selected market currently has no live quote available from the provider, so no scenario overlay is shown.")

st.caption("Data note: market observations are live when the provider returns them. Policy scenarios are simulations and are not presented as live forecasts.")
