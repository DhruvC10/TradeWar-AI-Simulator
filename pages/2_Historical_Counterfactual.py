import numpy as np
import streamlit as st
from utils import (
    inject_css, generate_trade_data, build_trade_network,
    build_country_scenario, build_teaching_explanation, render_teaching_panel,
    render_scenario_summary_metrics, render_overview_tab,
    render_forecast_tab, render_network_tab,
)

inject_css()

np.random.seed(42)
df = generate_trade_data()
G, _, _ = build_trade_network()

COUNTERFACTUAL_EVENTS = {
    "🇮🇳 1991 India — Faster liberalization": {
        "country": "India", "category": "Textiles", "target_partner": "US",
        "tariff_change": -25, "year_context": "1991",
        "what_really_happened": "India liberalised gradually under IMF conditions — phased tariff reductions over a decade.",
        "what_if": "India moved fast, cutting textile tariffs by 25% upfront — trying to capture the Asia export boom earlier.",
        "key_question": "Could India have become the garment powerhouse Bangladesh and Vietnam later became, if it had moved faster in 1991?",
    },
    "🇮🇳 1991 India — Resisted liberalization": {
        "country": "India", "category": "Electronics", "target_partner": "US",
        "tariff_change": 15, "year_context": "1991",
        "what_really_happened": "Crisis-forced liberalisation opened India's economy after the balance-of-payments crisis.",
        "what_if": "India resisted the IMF-linked reforms and maintained 15% higher protective tariffs on electronics.",
        "key_question": "How would continued protectionism have affected India's long-run electronics competitiveness?",
    },
    "🦠 2020 COVID — Vietnam trade stimulus": {
        "country": "Vietnam", "category": "Electronics", "target_partner": "US",
        "tariff_change": -18, "year_context": "2020",
        "what_really_happened": "Vietnam managed COVID well and maintained its electronics export sector with targeted carve-outs.",
        "what_if": "Vietnam aggressively slashed tariffs by 18% as a trade stimulus, positioning itself as the primary substitute for Chinese electronics.",
        "key_question": "Could aggressive tariff cuts in 2020 have accelerated Vietnam's electronics market share gain vs China by 3–5 years?",
    },
    "💰 2008 Financial Crisis — China keeps markets open": {
        "country": "China", "category": "Machinery", "target_partner": "US",
        "tariff_change": -12, "year_context": "2008",
        "what_really_happened": "China used targeted tariff adjustments and massive domestic stimulus to offset the demand collapse.",
        "what_if": "China kept machinery tariffs 12% lower and deepened cooperation with the US through the crisis.",
        "key_question": "Would a cooperative, low-tariff China in 2008 have avoided the geopolitical tensions that produced the 2018 trade war?",
    },
    "🇮🇳 2016 India Demonetization — Export alternative": {
        "country": "India", "category": "Textiles", "target_partner": "EU",
        "tariff_change": -20, "year_context": "2016",
        "what_really_happened": "India's demonetization in Nov 2016 disrupted the informal economy; GDP growth fell from ~8% to ~6%.",
        "what_if": "Instead of demonetization, India used a 20% textile tariff reduction to the EU as a growth stimulus.",
        "key_question": "Could an export-led strategy have delivered the black-money reduction goal without the economic disruption?",
    },
    "🇺🇸🇨🇳 2018 Trade War — China de-escalates": {
        "country": "China", "category": "Electronics", "target_partner": "US",
        "tariff_change": -20, "year_context": "2018",
        "what_really_happened": "China retaliated tit-for-tat; both sides imposed hundreds of billions in tariffs escalating through 2019.",
        "what_if": "China chose strategic non-retaliation — cutting electronics tariffs by 20% to de-escalate and protect export volumes.",
        "key_question": "Would de-escalation have preserved China's US market share better than the retaliatory strategy that pushed buyers toward Vietnam and India?",
    },
    "🇮🇳 India 2004 — Early semiconductor investment": {
        "country": "India", "category": "Semiconductors", "target_partner": "US",
        "tariff_change": -15, "year_context": "2004",
        "what_really_happened": "India invested heavily in IT services but largely missed the semiconductor manufacturing wave of the 2000s.",
        "what_if": "India established a PLI-like semiconductor incentive in 2004, cutting effective tariffs by 15% and attracting early fab investment.",
        "key_question": "Could a 20-year head start in semiconductor manufacturing have put India in Taiwan's position today?",
    },
    "🌏 2001 China WTO — Slower opening": {
        "country": "China", "category": "Machinery", "target_partner": "EU",
        "tariff_change": 12, "year_context": "2001",
        "what_really_happened": "China joined the WTO in Dec 2001, cutting tariffs and opening its markets rapidly — triggering the 'China shock' in global manufacturing.",
        "what_if": "China negotiated a slower WTO opening, keeping machinery tariffs 12% higher and limiting import competition.",
        "key_question": "Would a slower WTO opening have preserved more manufacturing employment in developed countries and avoided the political backlash that produced Trump's 2018 tariffs?",
    },
}

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.markdown("<h2 style='font-size:1.3rem;margin-bottom:0.75rem;'>🔄 Historical Event</h2>", unsafe_allow_html=True)
st.sidebar.info(
    "**What is a counterfactual?**\n\n"
    "A counterfactual asks: *what if a key decision had gone differently?* "
    "Select a historical event and the simulator models the alternative policy path."
)

selected_event = st.sidebar.selectbox("Select historical event", list(COUNTERFACTUAL_EVENTS.keys()))
cf = COUNTERFACTUAL_EVENTS[selected_event]
forecast_steps = st.sidebar.slider("Forecast horizon (years)", min_value=1, max_value=5, value=3, step=1)

country = cf["country"]
category = cf["category"]
target_partner = cf["target_partner"]
tariff_change = cf["tariff_change"]

# ── Main content ─────────────────────────────────────────────────────────────
st.title("🔄 Historical Counterfactual Analyzer")
st.markdown(
    '<p class="tw-muted" style="font-size:1.05rem;margin-top:-0.75rem;margin-bottom:1.5rem;">'
    "Explore how alternative historical decisions would have reshaped trade flows, forecasts, and supply chains"
    "</p>",
    unsafe_allow_html=True,
)

st.warning("⚠️ **Disclaimer**: All counterfactual scenarios are illustrative economic models, not validated historical claims. Use for teaching and structured reasoning only.")

# ── Event card ────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="tw-panel" style="margin:1.5rem 0;">'
    f'<p style="margin:0;font-size:0.72rem;font-weight:600;color:#7c3aed;text-transform:uppercase;letter-spacing:0.06em;">Counterfactual · {cf["year_context"]}</p>'
    f'<p style="margin:0.2rem 0 0.75rem 0;font-size:1rem;font-weight:700;">{selected_event}</p>'
    f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">'
    f'<div class="tw-panel-inner">'
    f'<p class="tw-muted" style="margin:0;font-size:0.7rem;font-weight:600;text-transform:uppercase;margin-bottom:0.3rem;">What actually happened</p>'
    f'<p style="margin:0;font-size:0.85rem;line-height:1.5;">{cf["what_really_happened"]}</p>'
    f'</div>'
    f'<div class="tw-panel-inner" style="border-color:#7c3aed40;">'
    f'<p style="margin:0;font-size:0.7rem;font-weight:600;color:#7c3aed;text-transform:uppercase;margin-bottom:0.3rem;">The alternative we\'re testing</p>'
    f'<p style="margin:0;font-size:0.85rem;line-height:1.5;">{cf["what_if"]}</p>'
    f'</div>'
    f'</div>'
    f'<p class="tw-muted" style="margin:0.75rem 0 0 0;font-size:0.85rem;font-style:italic;">Key question: {cf["key_question"]}</p>'
    f'</div>',
    unsafe_allow_html=True,
)

# Compute scenario
scenario = build_country_scenario(df, country, category, tariff_change, target_partner, projection_horizon=forecast_steps)
teaching = build_teaching_explanation(scenario, tariff_change)

# ── Summary metrics ───────────────────────────────────────────────────────────
st.markdown("### 📊 Counterfactual Summary")
render_scenario_summary_metrics(scenario)

# Outcome box
emoji = "📈" if tariff_change < 0 else "📉"
direction_word = "lower" if tariff_change < 0 else "higher"
_cf_border = "#4ade80" if tariff_change < 0 else "#f87171"
st.markdown(
    f'<div class="tw-panel" style="margin-top:1rem;">'
    f'<p style="margin:0;font-size:0.85rem;">'
    f'<strong>Counterfactual ({cf["year_context"]}):</strong> {abs(tariff_change)}% {direction_word} tariffs on {country}\'s {category} to {target_partner}'
    f'</p>'
    f'<p style="margin:0.5rem 0 0 0;font-size:1.05rem;font-weight:700;">'
    f'{emoji} Alternative path: <span class="tw-muted">${scenario["baseline_export_bn"]:.1f}B</span> → '
    f'${scenario["predicted_export_bn"]:.1f}B'
    f'<span class="tw-muted" style="font-size:0.85rem;font-weight:400;"> ({scenario["trade_change_pct"]:+.1f}%)</span>'
    f'</p>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Teaching explanation ───────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎓 Economic Analysis of the Counterfactual")
st.caption("Why would this alternative policy have produced the predicted outcome?")
render_teaching_panel(teaching)

st.markdown(
    f"""
    <div class="tw-panel" style="margin-top:1rem;">
        <p style="margin:0;font-size:0.9rem;">
        <strong>Counterfactual reasoning caveat:</strong>
        Real economies respond to policy changes through <em>many channels simultaneously</em>
        — investment flows, political responses, technology adoption, and consumer behaviour —
        that a tariff model cannot capture. These numbers show the <em>first-order trade effect</em> only.
        The further from {cf['year_context']}, the more uncertainty compounds.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Analysis tabs ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📈 Alternative History: What Would the Data Show?")
st.caption(f"Projecting what the trade data would look like if the {cf['year_context']} alternative policy had been enacted.")

overview_tab, forecast_tab, network_tab = st.tabs(["📊 Overview & Impact", "🔮 Forecast & Scenarios", "🕸️ Trade Network"])

with overview_tab:
    st.markdown(
        f"<p style='color:#6b7280;font-size:0.88rem;margin-bottom:1rem;'>"
        f"Estimated impact across all 10 economies if the {cf['year_context']} counterfactual policy had been in place, "
        f"projected to present using calibrated trade elasticity.</p>",
        unsafe_allow_html=True,
    )
    render_overview_tab(scenario, scenario["impact_df"])

with forecast_tab:
    st.markdown(
        f"<p style='color:#6b7280;font-size:0.88rem;margin-bottom:1rem;'>"
        f"Counterfactual export trajectory rooted at the {cf['year_context']} decision point. "
        f"The baseline reflects the actual historical path; the yellow line shows the alternative.</p>",
        unsafe_allow_html=True,
    )
    render_forecast_tab(df, country, category, tariff_change, forecast_steps)

with network_tab:
    st.markdown(
        f"<p style='color:#6b7280;font-size:0.88rem;margin-bottom:1rem;'>"
        f"Supply chain topology showing how {country}'s {category} network would have reorganised "
        f"under the {cf['year_context']} alternative policy.</p>",
        unsafe_allow_html=True,
    )
    render_network_tab(G, country, category, tariff_change, target_partner)

# ── About ─────────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📚 What is counterfactual analysis and why does it matter?", expanded=False):
    st.markdown(
        """
        **Counterfactual analysis** is the study of "what if" — a key method in economic history, policy evaluation, and
        strategic planning. Instead of describing what happened, it asks: *what would have happened if a key variable had been different?*

        **How economists use counterfactuals:**
        - **Policy evaluation**: Did a policy work, or would outcomes have been similar without it?
        - **Historical causation**: Was a specific event actually caused by the policy, or would it have occurred anyway?
        - **Scenario planning**: Which of several possible future policies produces the best outcome?

        **The limitations this tool acknowledges:**
        1. **First-order effects only**: This model captures the direct trade elasticity response. It does not model political reactions, investment reallocation, or second-round macroeconomic effects.
        2. **Partial equilibrium**: Trade flows change, but exchange rates, capital flows, and wages are held constant.
        3. **Compound uncertainty**: The further back the counterfactual event, the more other things would also have been different. A 1991 India without liberalisation is a very different economic world by 2024 — not just different trade numbers.

        **Educational value**: Counterfactuals force you to be explicit about causal mechanisms and assumptions.
        They are not meant to give definitive answers — they are structured ways of thinking about how policy choices shape economic paths.
        """
    )
