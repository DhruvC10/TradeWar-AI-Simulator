import streamlit as st


def learn_card(title, concept, explanation, example=None, formula=None, limitation=None):
    with st.expander(f"🎓 {title}"):
        st.markdown(f"**Key concept:** {concept}")
        st.write(explanation)
        if example:
            st.markdown(f"**Example:** {example}")
        if formula:
            st.markdown(f"**How it is calculated:** {formula}")
        if limitation:
            st.warning(f"**Important limitation:** {limitation}")


def concept_strip(items):
    cols = st.columns(min(len(items), 4))
    for col, (title, text) in zip(cols, items):
        with col:
            st.markdown(f"**{title}**")
            st.caption(text)


def explain_this(label, explanation, key):
    if st.button(f"💡 {label}", key=key, use_container_width=False):
        st.info(explanation)


def render_page_learning(page):
    lessons = {
        "financial": [
            ("What is a market index?", "An index tracks a basket of securities and summarizes how that market segment moves.", "The S&P 500 is an index; it is not the price of one company.", "Index return compares the index level over time.", "An index does not represent every company equally unless its methodology says so."),
            ("Returns vs. price", "A return measures the percentage change in an asset's value.", "If a price moves from 100 to 110, the simple return is +10%.", "Return = (new price / old price − 1) × 100.", "A return does not by itself explain why the price moved."),
            ("Volatility", "Volatility describes how much an asset's returns fluctuate.", "A market with frequent large moves is more volatile than one with small stable moves.", "A common historical measure is the standard deviation of returns.", "Historical volatility is backward-looking and is not a guarantee of future volatility."),
            ("Trade policy and markets", "Tariffs can affect company costs, demand, supply chains and expectations, which can influence asset prices.", "A tariff shock can affect an importer, its suppliers and firms that compete with them differently.", None, "The simulator's policy shock is illustrative; it is not an investment forecast."),
        ],
        "global": [
            ("Compare like with like", "Different indices have different constituents, currencies and methodologies.", "A percentage comparison is usually more informative than comparing raw index levels.", "Indexed performance starts every series at 100.", "Differences in market hours, currencies and index construction can affect comparisons."),
            ("Currency matters", "An overseas investment can change in local-market terms and in the investor's home currency.", "A foreign index can rise while a depreciating currency reduces the home-currency return.", "Approximate home-currency return combines asset and FX changes.", "This explorer does not automatically convert every series into one currency."),
            ("Market vs. economy", "A stock index is not the same thing as GDP, employment or household welfare.", "Markets incorporate expectations about future profits and policy, not only current output.", None, "Do not interpret an index move as a complete measure of economic health."),
            ("Diversification", "Different markets can respond differently to the same global shock.", "Comparing markets can reveal whether a shock appears broad or concentrated.", None, "Correlation can change across regimes and crisis periods."),
        ],
        "historical": [
            ("Descriptive statistics", "Means, medians, standard deviations and ranges summarize the observed dataset.", "They help you understand scale and dispersion before modelling.", "The mean is the arithmetic average.", "Descriptive statistics do not establish causal relationships."),
            ("Correlation is not causation", "Correlation measures co-movement, not whether one variable causes another.", "Exports and GDP can move together because of a third factor.", "Correlation ranges from −1 to +1.", "A strong correlation can be spurious, confounded or driven by trends."),
            ("OLS regression", "OLS estimates the relationship between an outcome and selected predictors.", "A tariff coefficient estimates the modelled change in exports associated with a one-unit tariff change, conditional on the included controls.", "The coefficient is the slope holding the other selected variables constant.", "Observational regression can suffer from omitted variables, reverse causality and measurement error."),
            ("Elasticity", "Elasticity measures proportional responsiveness.", "A negative demand elasticity means a relative price increase is associated with lower quantity demanded.", "ΔQ/Q = ε × ΔP/P.", "The simulator uses a transparent partial-equilibrium approximation; it is not a full general-equilibrium model."),
            ("ARIMA forecasting", "ARIMA models time-series dynamics using autoregressive, differencing and moving-average components.", "It uses the historical series itself to generate a baseline forecast.", "The model is fitted to past observations and produces a forecast interval.", "Forecast uncertainty grows with horizon and structural breaks can make historical patterns unreliable."),
            ("Difference-in-Differences", "DiD estimates an intervention effect by comparing changes across treated and untreated groups.", "A credible design needs a defensible control group and a parallel-trends assumption.", "The interaction term represents the DiD effect.", "The app's single-series teaching mode is not publication-quality causal identification."),
        ],
    }
    for args in lessons.get(page, []):
        learn_card(*args)


def render_learning_header(title, subtitle):
    st.markdown(f"### 🎓 Learn: {title}")
    st.caption(subtitle)
