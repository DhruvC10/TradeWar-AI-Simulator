import pandas as pd
import streamlit as st
from market_data import MARKETS, COMMON_ASSETS, download_history, summarize, live_timestamp
from theme import inject_css, render_chart, make_line_figure
from components.learning import render_learning_header, render_page_learning

st.set_page_config(page_title="Global Market Explorer", page_icon="🌐", layout="wide")
inject_css()

st.title("🌐 Global Financial Market Explorer")
st.caption("Live market data from the exchange/provider available for each instrument. Yahoo Finance is used for supported markets; Bangladesh DSE instruments use the DSE adapter. South Africa's Top 40 entry is an explicitly labelled ETF proxy.")
st.caption(f"Last market refresh: {live_timestamp()} • Prices can be delayed depending on the exchange/data provider.")

country = st.selectbox("Country / market", list(MARKETS))
period = st.selectbox("History", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

market_options = MARKETS[country]
market_labels = {f"{name} ({ticker})": (name, ticker, asset_type) for name, ticker, asset_type in market_options}
selected_labels = st.multiselect("Indices / markets to compare", list(market_labels), default=list(market_labels)[:2])

render_learning_header("Global markets", "Understand indices, currencies and cross-market comparisons before drawing conclusions.")
render_page_learning("global")
rows = []
charts = []
for label in selected_labels:
    name, ticker, asset_type = market_labels[label]
    data = download_history(ticker, period)
    if data.empty or "Close" not in data:
        st.warning(f"No live data returned for {name} ({ticker}).")
        continue
    close = pd.to_numeric(data["Close"], errors="coerce").dropna()
    if close.empty:
        continue
    latest = float(close.iloc[-1]); previous = float(close.iloc[-2]) if len(close) > 1 else latest
    start = float(close.iloc[0])
    rows.append({"Market": name, "Ticker": ticker, "Type": asset_type, "Latest": round(latest, 2), "Daily %": round((latest / previous - 1) * 100, 2), "Period %": round((latest / start - 1) * 100, 2), "Observations": len(close)})
    charts.append((name, close))

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    for name, close in charts:
        st.subheader(name)
        render_chart(make_line_figure([(name, close)], title=f"{name} — {period}", yaxis_title="Index / price"), key=f"global_{name}_{period}")
else:
    st.info("Select one or more markets to load live data.")

st.divider()
st.subheader(f"📊 Major listed assets — {country}")
assets = COMMON_ASSETS.get(country, [])
if assets:
    asset_rows = []
    for name, ticker, asset_type in assets:
        result = summarize(ticker, name)
        if result:
            asset_rows.append({"Asset": name, "Ticker": ticker, "Type": asset_type, "Latest": round(result["latest"], 2), "Daily %": round(result["daily_pct"], 2), "1Y %": round(result["period_pct"], 2), "Volume": result["volume"]})
    if asset_rows:
        st.dataframe(pd.DataFrame(asset_rows), use_container_width=True, hide_index=True)
else:
    st.caption("No curated company list is configured for this market yet. Use the ticker search below.")

st.divider()
st.subheader("🔎 Any Yahoo Finance instrument")
custom = st.text_input("Enter ticker", placeholder="RELIANCE.NS, TCS.NS, AAPL, MSFT, NVDA, 0700.HK")
custom_period = st.selectbox("Custom ticker history", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3, key="custom_period")
if custom.strip():
    data = download_history(custom.strip(), custom_period)
    if data.empty:
        st.warning("No data found. Check the ticker symbol and exchange suffix.")
    else:
        result = summarize(custom.strip())
        if result:
            a, b, c = st.columns(3)
            a.metric("Latest", f"{result['latest']:,.2f}")
            b.metric("Daily change", f"{result['daily_pct']:+.2f}%")
            c.metric("1Y change", f"{result['period_pct']:+.2f}%")
        custom_close = pd.to_numeric(data["Close"], errors="coerce").dropna()
        render_chart(make_line_figure([(custom.strip(), custom_close)], title=f"{custom.strip()} — {custom_period}", yaxis_title="Price"), key="global_custom_ticker")
