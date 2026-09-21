import numpy as np
import streamlit as st
from utils import (
    COUNTRIES, CATEGORIES,
    inject_css, generate_trade_data,
    build_country_scenario, build_teaching_explanation, render_teaching_panel,
    apply_policy_shock_to_scenario, build_policy_shock_summary,
    render_scenario_summary_metrics, render_overview_tab,
    render_forecast_tab,
)
from trade_network import render_network_tab

inject_css()
np.random.seed(42)
df = generate_trade_data()

PRESET_GROUPS = {
    "🌍 Global Trade War": {
        "US tariffs on China electronics (+25%)": {"country": "China", "category": "Electronics", "target_partner": "US", "tariff_change": 25},
        "US tariffs on China semiconductors (+20%)": {"country": "China", "category": "Semiconductors", "target_partner": "US", "tariff_change": 20},
        "EU tariffs on Vietnam textiles (+15%)": {"country": "Vietnam", "category": "Textiles", "target_partner": "EU", "tariff_change": 15},
        "US-China Phase 1 deal reversal: machinery (+20%)": {"country": "China", "category": "Machinery", "target_partner": "US", "tariff_change": 20},
        "Taiwan chip export block to China (+30%)": {"country": "Taiwan", "category": "Semiconductors", "target_partner": "China", "tariff_change": 30},
        "EU carbon border tariff on Chinese steel (+25%)": {"country": "China", "category": "Steel", "target_partner": "EU", "tariff_change": 25},
        "South Korea–Japan semiconductor rivalry (–10%)": {"country": "South Korea", "category": "Semiconductors", "target_partner": "US", "tariff_change": -10},
    },
    "🇮🇳 India Trade Scenarios": {
        "India: Atma Nirbhar — import tariff on Chinese electronics (+30%)": {"country": "China", "category": "Electronics", "target_partner": "India", "tariff_change": 30},
        "India: PLI semiconductor boost — US cuts tariffs on India (–12%)": {"country": "India", "category": "Semiconductors", "target_partner": "US", "tariff_change": -12},
        "India: Textile FTA with EU — EU cuts tariffs (–15%)": {"country": "India", "category": "Textiles", "target_partner": "EU", "tariff_change": -15},
        "India: API chemical import tariff on China (+20%)": {"country": "China", "category": "Chemicals", "target_partner": "India", "tariff_change": 20},
        "India: Steel anti-dumping tariff on China (+25%)": {"country": "China", "category": "Steel", "target_partner": "India", "tariff_change": 25},
        "India: Electronics export push to US — US lowers tariffs (–8%)": {"country": "India", "category": "Electronics", "target_partner": "US", "tariff_change": -8},
        "India: US tariffs on Indian semiconductors (+20%)": {"country": "India", "category": "Semiconductors", "target_partner": "US", "tariff_change": 20},
        "India: Dependency shift — away from Chinese electronics (–18%)": {"country": "India", "category": "Electronics", "target_partner": "China", "tariff_change": -18},
        "India: EU FTA on chemicals and pharma (–20%)": {"country": "India", "category": "Chemicals", "target_partner": "EU", "tariff_change": -20},
        "India: US tech tariff friction — machinery proxy (+10%)": {"country": "India", "category": "Machinery", "target_partner": "US", "tariff_change": 10},
        "India vs Vietnam: textiles race in EU market (+12% on India)": {"country": "India", "category": "Textiles", "target_partner": "EU", "tariff_change": 12},
        "India: Bangladesh garment competition — Bangladesh gets EU cut (–12%)": {"country": "Bangladesh", "category": "Textiles", "target_partner": "EU", "tariff_change": -12},
    },
    "🏭 Supply Chain Diversification": {
        "Vietnam gains as China loses: electronics to US": {"country": "Vietnam", "category": "Electronics", "target_partner": "US", "tariff_change": -8},
        "Bangladesh textile boom: US lowers tariffs (–20%)": {"country": "Bangladesh", "category": "Textiles", "target_partner": "US", "tariff_change": -20},
        "Thailand: auto parts & machinery boost to US (–10%)": {"country": "Thailand", "category": "Machinery", "target_partner": "US", "tariff_change": -10},
        "India replaces China in US electronics supply chain (–15%)": {"country": "India", "category": "Electronics", "target_partner": "US", "tariff_change": -15},
        "Taiwan dominant in semiconductors — US further lowers (–8%)": {"country": "Taiwan", "category": "Semiconductors", "target_partner": "US", "tariff_change": -8},
    },
    "📉 Trade War Escalations": {
        "Full escalation: US +30% on all China electronics": {"country": "China", "category": "Electronics", "target_partner": "US", "tariff_change": 30},
        "China retaliates: +25% on US machinery": {"country": "US", "category": "Machinery", "target_partner": "China", "tariff_change": 25},
        "EU–US trade friction: steel tariffs (+20%)": {"country": "EU", "category": "Steel", "target_partner": "US", "tariff_change": 20},
        "India–China border escalation: all categories (+25%)": {"country": "China", "category": "Machinery", "target_partner": "India", "tariff_change": 25},
    },
}
PRESET_FLAT = {"— Custom (set your own below) —": {"country": "China", "category": "Electronics", "target_partner": "US", "tariff_change": 10}}
for group_label, presets in PRESET_GROUPS.items():
    for key, value in presets.items():
        PRESET_FLAT[f"{group_label} › {key}"] = value

st.sidebar.markdown("<h2 style='font-size:1.3rem;margin-bottom:.75rem;'>⚙️ Build Your Scenario</h2>", unsafe_allow_html=True)
st.sidebar.caption("**Step 1:** Choose a preset or build your own. **Step 2:** Fine-tune below.")
preset_key = st.sidebar.selectbox("Scenario preset", list(PRESET_FLAT.keys()))
selected = PRESET_FLAT[preset_key]
st.sidebar.divider()
st.sidebar.markdown("**Step 2 — Fine-tune the scenario parameters**")

country = st.sidebar.selectbox("Affected exporter", COUNTRIES, index=COUNTRIES.index(selected["country"]), help="Which country's exports are being hit by the tariff?")
category_options = list(CATEGORIES)
category = st.sidebar.selectbox("Product category", category_options, index=category_options.index(selected["category"]))
partners = ["US", "EU", "China", "India", "Japan", "South Korea"]
selected_partner = selected["target_partner"] if selected["target_partner"] in partners else "US"
target_partner = st.sidebar.selectbox("Tariff imposer (importer)", partners, index=partners.index(selected_partner))
tariff_change = st.sidebar.slider("Tariff change (%)", min_value=-30, max_value=30, value=selected["tariff_change"], step=1, help="Positive = tariff increase. Negative = tariff reduction.")
forecast_steps = st.sidebar.slider("Forecast horizon (years)", min_value=1, max_value=5, value=3, step=1)

if tariff_change > 0:
    direction_hint, hint_color = "Tariff increase — exporter loses", "#f87171"
elif tariff_change < 0:
    direction_hint, hint_color = "Tariff reduction — exporter gains", "#4ade80"
else:
    direction_hint, hint_color = "No change from baseline", "#94a3b8"
st.sidebar.markdown(f'<div class="tw-hint" style="border-left:3px solid {hint_color};"><p style="margin:0;font-size:.82rem;font-weight:600;color:{hint_color};">{direction_hint}</p></div>', unsafe_allow_html=True)

st.sidebar.divider()
st.sidebar.markdown("**Optional: Historical shock overlay**")
historical_event = st.sidebar.selectbox("Historical policy shock", ["None", "Post-9/11 US financial stabilization", "COVID-19 trade disruption", "India 2016 demonetization shock"])
shock_pct = st.sidebar.slider("Shock intensity (%)", min_value=-20, max_value=20, value=5, step=1)

st.title("⚙️ Custom Scenario Simulator")
st.markdown('<p class="tw-muted" style="font-size:1.05rem;margin-top:-.75rem;margin-bottom:1.5rem;">Model how tariff changes ripple through supply chains, forecasts, and trade networks — with step-by-step economic explanations</p>', unsafe_allow_html=True)
tariff_direction_word = "increase" if tariff_change > 0 else "reduction" if tariff_change < 0 else "no change"
_ctx_border = "#f87171" if tariff_change > 0 else "#4ade80" if tariff_change < 0 else "#94a3b8"
raise_word = "raises" if tariff_change > 0 else "cuts" if tariff_change < 0 else "keeps"
context_html = f'<div class="tw-panel"><p style="margin:0;font-size:.95rem;font-weight:600;">{abs(tariff_change)}% tariff {tariff_direction_word} &nbsp;·&nbsp; {country} → {target_partner} &nbsp;·&nbsp; {category}</p><p class="tw-muted" style="margin:.3rem 0 0;font-size:.82rem;">{target_partner} {raise_word} tariffs on {country}\'s {category} by {abs(tariff_change)}%. Trade elasticity applied across all 10 economies.</p></div>'
st.markdown(context_html, unsafe_allow_html=True)

scenario = build_country_scenario(df, country, category, tariff_change, target_partner, projection_horizon=forecast_steps)
scenario = apply_policy_shock_to_scenario(scenario, historical_event, shock_pct)
teaching = build_teaching_explanation(scenario, tariff_change)

st.markdown("### 📊 Scenario Summary")
render_scenario_summary_metrics(scenario)
st.markdown("<br/>", unsafe_allow_html=True)
emoji = "📉" if tariff_change > 0 else "📈" if tariff_change < 0 else "➡️"
st.markdown(f'<div class="tw-panel"><p style="margin:0;font-size:.88rem;"><strong>{abs(tariff_change)}% tariff {tariff_direction_word}</strong> on <strong>{country}\'s {category}</strong> exports to <strong>{target_partner}</strong></p><p style="margin:.6rem 0 0;font-size:1.1rem;font-weight:700;">{emoji} Predicted exports: <span class="tw-muted">${scenario["baseline_export_bn"]:.1f}B</span> → ${scenario["predicted_export_bn"]:.1f}B<span class="tw-muted" style="font-size:.85rem;font-weight:400;"> ({scenario["trade_change_pct"]:+.1f}% | ${scenario["trade_delta_bn"]:+.1f}B)</span></p></div>', unsafe_allow_html=True)
if historical_event != "None":
    st.info(f"⚙️ **Historical shock also applied:** {build_policy_shock_summary(historical_event, shock_pct)}")

st.markdown("### 🎯 Who benefits in this scenario?")
b_type = scenario.get("beneficiary_type", "none")
status = scenario.get("beneficiary_status", "limited")
beneficiaries = scenario.get("likely_beneficiaries", [])
col_ben1, col_ben2 = st.columns(2, gap="medium")
with col_ben1:
    if beneficiaries and b_type == "diversion":
        title = "🚀 Trade diversion beneficiaries"
        label = f"Alternative suppliers capturing trade diverted away from {country}"
    elif beneficiaries and b_type == "gain":
        title = "🏆 Beneficiaries of lower tariffs"
        label = f"Countries benefiting from {country}'s improved access to {target_partner}"
    elif status == "baseline":
        title = "➡️ Baseline scenario"
        label = "No tariff change was applied, so there is no incremental beneficiary effect."
    else:
        title = "📊 Limited beneficiary effect"
        label = "The model detects a beneficiary effect, but it is small at this tariff magnitude."
    body = ", ".join(beneficiaries) if beneficiaries else "No country crosses the significance floor for this scenario."
    st.info(f"**{title}**\n\n**{body}**\n\n{label}")

with col_ben2:
    diversion_pool = sum(scenario.get("trade_diversion", {}).values())
    if diversion_pool > 0:
        pool_label = "Estimated trade diverted to alternatives" if b_type == "diversion" else "Estimated export revenue gain"
        st.metric(pool_label, f"${diversion_pool:.2f}B")
        st.caption("Model estimate per year; not a live trade-flow measurement.")
    else:
        st.info("Trade flows remain near equilibrium — no incremental beneficiary pool.")

st.markdown("---")
st.markdown("### 🎓 Economics Explanation")
st.caption("Understand why these outputs are predicted — the mechanism behind the numbers.")
render_teaching_panel(teaching)
st.markdown("---")
st.markdown("### 📈 Deep-Dive Analysis")
overview_tab, forecast_tab, network_tab = st.tabs(["📊 Overview & Impact", "🔮 Forecast & Scenarios", "🕸️ Trade Network"])
with overview_tab:
    render_overview_tab(scenario, scenario["impact_df"])
with forecast_tab:
    render_forecast_tab(df, country, category, tariff_change, forecast_steps)
with network_tab:
    render_network_tab(country, category, tariff_change, target_partner)

st.markdown("---")
with st.expander("📚 How this simulator works", expanded=False):
    elasticity_val = scenario.get("elasticity", None)
    if elasticity_val is None:
        from beneficiary import TRADE_ELASTICITY
        elasticity_val = TRADE_ELASTICITY.get(category, -0.7)
    st.markdown(f"""
    **Core formula**: Export change (%) = Trade elasticity × Tariff change (%)

    - Selected category: **{category}** | Elasticity: **{elasticity_val:.1f}**
    - Applied tariff: **{tariff_change:+.0f}%**
    - Predicted trade response: **{elasticity_val * tariff_change:.1f}%** (before horizon adjustment)

    **Beneficiary significance:** The ranking uses the scenario's own trade shock to set a small relative significance floor; it does not use a fixed $0.5B cutoff.
    """)
