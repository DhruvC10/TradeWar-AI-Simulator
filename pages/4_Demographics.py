import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils import (
    COUNTRIES, YEARS, COUNTRY_PROFILES,
    inject_css, generate_trade_data, forecast_series,
)

inject_css()

np.random.seed(42)
df = generate_trade_data()

AGE_LABELS = ["0-14", "15-29", "30-44", "45-59", "60+"]

SECTOR_DESCRIPTIONS = {
    "Primary": "Agriculture, fishing, mining — extraction of raw materials. Highly trade-exposed to commodity tariffs.",
    "Secondary": "Manufacturing, construction — transformation of raw materials into goods. Directly affected by industrial tariffs.",
    "Tertiary": "Services, retail, transport — supports the first two sectors. Indirectly affected through demand channels.",
    "Quaternary": "Knowledge, IT, research, finance — the information economy. Affected by digital trade and IP rules.",
}


def build_population_pyramid(profile, country):
    age_dist = profile.get("age_distribution", {"0-14": 20, "15-29": 22, "30-44": 22, "45-59": 20, "60+": 16})
    pop = profile.get("population_mn", 100)
    ages = list(age_dist.keys())
    male_pct = [v * 0.495 for v in age_dist.values()]
    female_pct = [v * 0.505 for v in age_dist.values()]
    male_pop = [round(p / 100 * pop, 1) for p in male_pct]
    female_pop = [round(p / 100 * pop, 1) for p in female_pct]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=ages, x=[-v for v in male_pop], orientation="h",
        name="Male", marker_color="#4facfe",
        hovertemplate="<b>%{y}</b><br>Male: %{customdata:.1f}M<extra></extra>",
        customdata=male_pop,
    ))
    fig.add_trace(go.Bar(
        y=ages, x=female_pop, orientation="h",
        name="Female", marker_color="#f093fb",
        hovertemplate="<b>%{y}</b><br>Female: %{customdata:.1f}M<extra></extra>",
        customdata=female_pop,
    ))
    max_val = max(male_pop + female_pop) * 1.15
    tick_values = [-max_val * 0.75, -max_val * 0.5, -max_val * 0.25, 0, max_val * 0.25, max_val * 0.5, max_val * 0.75]
    fig.update_layout(
        title=f"Population Pyramid — {country}",
        xaxis=dict(
            title="Population (millions)",
            tickvals=tick_values,
            ticktext=[f"{abs(v):.0f}M" for v in tick_values],
            range=[-max_val, max_val],
        ),
        yaxis_title="Age group",
        barmode="overlay",
        template="plotly_white",
        height=360,
        bargap=0.1,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        uirevision=f"{country}_{round(pop, 3)}_{','.join(f'{age_dist.get(a, 0):.2f}' for a in ages)}",
    )
    return fig


def build_sector_chart(profile, country):
    sectors = ["Primary", "Secondary", "Tertiary", "Quaternary"]
    values = [
        float(profile.get("primary_sector_pct", 20)),
        float(profile.get("secondary_sector_pct", 30)),
        float(profile.get("tertiary_sector_pct", 45)),
        float(profile.get("quaternary_sector_pct", 5)),
    ]
    colors = ["#43e97b", "#4facfe", "#f093fb", "#ffd166"]
    fig = px.pie(
        names=sectors, values=values,
        title=f"Workforce Sector Breakdown — {country}",
        color_discrete_sequence=colors,
        hole=0.4,
    )
    fig.update_traces(textinfo="label+percent", hovertemplate="<b>%{label}</b><br>%{value:.2f}% of workforce<extra></extra>")
    fig.update_layout(
        template="plotly_white",
        height=360,
        showlegend=True,
        uirevision=f"{country}_{','.join(f'{v:.2f}' for v in values)}",
    )
    return fig


def build_population_forecast(profile, years_ahead=10, fertility_adj=0.0, migration_adj=0.0):
    pop = profile.get("population_mn", 100)
    median_age = profile.get("median_age", 35)
    base_growth = max(0.001, (50 - median_age) / 1000 + 0.005)

    historical_pops = [pop * (1 - base_growth) ** (2024 - y) for y in YEARS]
    future_years = list(range(2025, 2025 + years_ahead))
    future_pops_baseline = [pop * (1 + base_growth) ** i for i in range(1, years_ahead + 1)]
    migration_rate = migration_adj / max(pop * 1000, 1)
    scenario_growth = base_growth + fertility_adj / 100 + migration_rate
    scenario_growth = max(-0.05, min(0.08, scenario_growth))
    future_pops_scenario = [pop * (1 + scenario_growth) ** i for i in range(1, years_ahead + 1)]
    return list(YEARS), historical_pops, future_years, future_pops_baseline, future_pops_scenario


def apply_demographic_scenario(profile, years_ahead, fertility_adj, migration_adj):
    """Project every Overview/Impact input from the selected demographic scenario."""
    scenario = dict(profile)
    base_pop = float(profile.get("population_mn", 100))
    base_age = float(profile.get("median_age", 35))
    base_growth = max(0.001, (50 - base_age) / 1000 + 0.005)
    migration_rate = migration_adj / max(base_pop * 1000, 1)
    scenario_growth = base_growth + fertility_adj / 100 + migration_rate
    scenario_growth = max(-0.05, min(0.08, scenario_growth))

    projected_pop = base_pop * (1 + scenario_growth) ** years_ahead
    scenario["population_mn"] = round(projected_pop, 1)

    age_dist = dict(profile.get("age_distribution", {}))
    if age_dist:
        # Apply scenario effects to cohort shares, then normalize. This makes the
        # population pyramid itself respond to fertility and migration, not only the metrics.
        fertility_shift = float(np.clip(fertility_adj * years_ahead * 0.30, -12, 12))
        migration_shift = float(np.clip((migration_adj / 1000.0) * years_ahead * 0.20, -12, 12))

        age_dist["0-14"] = age_dist.get("0-14", 20) + fertility_shift
        age_dist["15-29"] = age_dist.get("15-29", 22) + fertility_shift * 0.45 + migration_shift * 0.75
        age_dist["30-44"] = age_dist.get("30-44", 22) + migration_shift * 0.50
        age_dist["45-59"] = age_dist.get("45-59", 20) - fertility_shift * 0.15
        age_dist["60+"] = age_dist.get("60+", 16) - fertility_shift * 0.30 - migration_shift * 0.25

        age_dist = {k: max(0.1, float(v)) for k, v in age_dist.items()}
        total = sum(age_dist.values())
        scenario["age_distribution"] = {k: round(v / total * 100, 2) for k, v in age_dist.items()}

        young_share = scenario["age_distribution"].get("0-14", 20)
        older_share = scenario["age_distribution"].get("60+", 16)
        scenario["median_age"] = round(float(np.clip(base_age + (older_share - young_share) * 0.08, 15, 70)), 1)

    base_participation = float(profile.get("labor_force_mn", 0)) / max(base_pop, 1)
    working_share = sum(scenario.get("age_distribution", {}).get(k, 0) for k in ["15-29", "30-44", "45-59"]) / 100
    if working_share > 0:
        scenario["labor_force_mn"] = round(projected_pop * min(0.95, base_participation * (working_share / max(0.65, base_participation))), 1)
    else:
        scenario["labor_force_mn"] = round(projected_pop * base_participation, 1)

    # Project sector shares from the same scenario horizon and normalize them so
    # the pie chart remains a true workforce composition.
    sector_changes = {
        "Primary": -0.5 * years_ahead / 5,
        "Secondary": 0.2 * years_ahead / 5,
        "Tertiary": 0.25 * years_ahead / 5,
        "Quaternary": 0.05 * years_ahead / 5,
    }
    sector_keys = [
        ("Primary", "primary_sector_pct"),
        ("Secondary", "secondary_sector_pct"),
        ("Tertiary", "tertiary_sector_pct"),
        ("Quaternary", "quaternary_sector_pct"),
    ]
    sector_values = {}
    for sector, key in sector_keys:
        base_pct = float(profile.get(key, 0))
        # Scenario assumptions affect the structural trajectory; fertility/migration
        # also have a small workforce-composition effect.
        scenario_effect = migration_rate * years_ahead * (1.5 if sector in ("Secondary", "Tertiary") else 0.5)
        sector_values[key] = max(0.5, base_pct + sector_changes[sector] + scenario_effect)
    sector_total = sum(sector_values.values())
    for key, value in sector_values.items():
        scenario[key] = round(value / sector_total * 100, 2)

    scenario["scenario_year"] = 2024 + years_ahead
    return scenario


def classify_demographic(profile):
    age = profile.get("median_age", 35)
    agri = profile.get("primary_sector_pct", 20)
    labor = profile.get("labor_force_mn", 50)
    pop = profile.get("population_mn", 100)
    participation = (labor / pop * 100) if pop > 0 else 50

    if age < 30 and agri > 30:
        phase = "Pre-industrial transition"
        desc = "Large agricultural workforce and young population. High tariff sensitivity in primary commodities. Strong demographic dividend potential if industrial jobs expand."
        color, border = "#fef3c7", "#f59e0b"
    elif age < 35 and agri < 30:
        phase = "Industrial growth phase"
        desc = "Young, increasingly urbanised workforce. Manufacturing tariffs have large employment effects. High growth potential; vulnerable to external demand shocks."
        color, border = "#dcfce7", "#22c55e"
    elif age < 42:
        phase = "Mature industrial economy"
        desc = "Balanced age structure with diversified sector base. Trade shocks absorbed across multiple sectors. Moderate demographic risk."
        color, border = "#eff6ff", "#3b82f6"
    else:
        phase = "Post-industrial aging economy"
        desc = "Aging population constrains labour supply and raises social costs. Tariff shocks fall heavily on services and knowledge sectors. Structural vulnerability to workforce shrinkage."
        color, border = "#fee2e2", "#ef4444"
    return phase, desc, color, border


st.sidebar.markdown("<h2 style='font-size:1.4rem;margin-bottom:1rem;'>👥 Demographic Settings</h2>", unsafe_allow_html=True)
country = st.sidebar.selectbox("Select country", COUNTRIES, key="demographics_country")
base_profile = dict(COUNTRY_PROFILES.get(country, {}))

compare_options = [c for c in COUNTRIES if c != country]
if st.session_state.get("demographics_compare_country") not in compare_options:
    st.session_state["demographics_compare_country"] = compare_options[0]
compare_country = st.sidebar.selectbox("Compare with", compare_options, key="demographics_compare_country")
compare_profile = dict(COUNTRY_PROFILES.get(compare_country, {}))

st.sidebar.divider()
st.sidebar.markdown("**Population scenario parameters**")
fertility_adj = st.sidebar.slider(
    "Fertility rate adjustment (%/yr)", min_value=-2.0, max_value=2.0, value=0.0, step=0.1,
    help="Positive = higher birth rate; negative = lower birth rate", key="demographics_fertility"
)
migration_adj = st.sidebar.slider(
    "Net migration (thousands/yr)", min_value=-500, max_value=500, value=0, step=50,
    help="Positive = net inflow; negative = net outflow", key="demographics_migration"
)
forecast_years = st.sidebar.slider(
    "Forecast horizon (years)", min_value=5, max_value=30, value=15, step=5,
    key="demographics_forecast_years"
)

profile = apply_demographic_scenario(base_profile, forecast_years, fertility_adj, migration_adj)
scenario_year = profile.get("scenario_year", 2024 + forecast_years)
view_signature = f"{country}_{compare_country}_{fertility_adj}_{migration_adj}_{forecast_years}".replace(" ", "_")

st.title("👥 Demographics")
st.markdown(
    '<p class="tw-muted" style="font-size:1.1rem;margin-top:-1rem;margin-bottom:1.5rem;">'
    "Population structure, workforce composition, sector breakdowns, and demographic forecasts"
    "</p>",
    unsafe_allow_html=True,
)

pop = profile.get("population_mn", 0)
labor = profile.get("labor_force_mn", 0)
age = profile.get("median_age", 0)
urban = profile.get("urbanization_pct", 0)
agri = profile.get("primary_sector_pct", 0)
participation = round((labor / pop * 100), 1) if pop > 0 else 0

st.markdown(
    f'<div class="tw-panel">'
    f'<p style="margin:0;font-size:0.72rem;font-weight:600;color:#16a34a;text-transform:uppercase;letter-spacing:0.06em;">Demographic Scenario Profile</p>'
    f'<p style="margin:0.2rem 0 0 0;font-size:0.98rem;font-weight:700;">{country} — {scenario_year} snapshot</p>'
    f'<p class="tw-muted" style="margin:0.3rem 0 0 0;font-size:0.82rem;">'
    f'Population: {pop:,}M &nbsp;·&nbsp; Labour force: {labor:,}M &nbsp;·&nbsp; Median age: {age} yrs &nbsp;·&nbsp; '
    f'Urbanisation: {urban}% &nbsp;·&nbsp; Labour participation: {participation:.0f}%'
    f'</p>'
    f'</div>',
    unsafe_allow_html=True,
)

col1, col2, col3, col4, col5 = st.columns(5, gap="small")
with col1:
    st.metric("👥 Population", f"{pop:,}M", help="Projected population under the selected demographic scenario")
with col2:
    st.metric("💼 Labour Force", f"{labor:,}M", help="Projected labour force under the selected demographic scenario")
with col3:
    age_emoji = "👴" if age > 42 else "👨" if age > 32 else "👶"
    st.metric(f"{age_emoji} Median Age", f"{age} yrs")
with col4:
    st.metric("🏙️ Urbanisation", f"{urban}%")
with col5:
    st.metric("⚡ Labour Participation", f"{participation:.0f}%")

st.markdown("<hr style='margin:1.5rem 0;'/>", unsafe_allow_html=True)

phase, phase_desc, phase_color, phase_border = classify_demographic(profile)
st.markdown(
    f'<div class="tw-panel">'
    f'<p style="margin:0 0 0.25rem 0;font-weight:700;font-size:1rem;">📊 Demographic phase: {phase}</p>'
    f'<p style="margin:0;font-size:0.9rem;line-height:1.6;">{phase_desc}</p>'
    f"</div>",
    unsafe_allow_html=True,
)

overview_tab, forecast_tab, compare_tab = st.tabs(["📊 Overview & Impact", "🔮 Forecast & Scenarios", "🌍 Country Comparison"])

with overview_tab:
    st.markdown(f"<h3 style='margin-bottom:1rem;'>📊 Population Structure & Sector Breakdown — {scenario_year}</h3>", unsafe_allow_html=True)
    col_pyramid, col_sector = st.columns(2, gap="large")
    with col_pyramid:
        st.plotly_chart(build_population_pyramid(profile, country), use_container_width=True, key=f"overview_pyramid_{view_signature}")
        age_dist = profile.get("age_distribution", {})
        working_age = age_dist.get("15-29", 0) + age_dist.get("30-44", 0) + age_dist.get("45-59", 0)
        dependency_ratio = round((age_dist.get("0-14", 0) + age_dist.get("60+", 0)) / max(working_age, 1) * 100, 1)
        st.markdown(
            f'<div class="tw-panel"><p style="margin:0;font-size:0.9rem;">Dependency ratio: <strong>{dependency_ratio:.0f}%</strong> '
            f'(dependants per 100 working-age people). '
            f'{"High dependency = greater social spending burden." if dependency_ratio > 55 else "Moderate dependency = manageable support ratio."}'
            f'</p></div>', unsafe_allow_html=True,
        )
    with col_sector:
        st.plotly_chart(build_sector_chart(profile, country), use_container_width=True, key=f"overview_sector_{view_signature}")
        st.markdown("**Sector descriptions**")
        for sector, desc in SECTOR_DESCRIPTIONS.items():
            pct_key = f"{sector.lower()}_sector_pct"
            pct = profile.get(pct_key, 0)
            st.markdown(
                f'<div class="tw-hint" style="margin-bottom:0.5rem;"><p style="margin:0;font-size:0.85rem;"><strong>{sector} ({pct}%)</strong>: {desc}</p></div>',
                unsafe_allow_html=True,
            )
    st.markdown("<hr style='margin:2rem 0;'/>", unsafe_allow_html=True)
    st.markdown("<h4 style='margin-bottom:1rem;'>⚖️ Demographic Vulnerability to Trade Shocks</h4>", unsafe_allow_html=True)
    col_v1, col_v2 = st.columns(2, gap="medium")
    with col_v1:
        if agri > 30:
            agri_text = f"🌾 <strong>High agricultural workforce ({agri:.0f}%)</strong> — Commodity tariffs translate directly to rural job losses and urban migration pressure. Politically sensitive for governments."
        elif agri < 5:
            agri_text = f"✓ <strong>Low agricultural exposure ({agri:.0f}%)</strong> — Manufacturing and service tariffs dominate. Less rural vulnerability; shock absorbed in urban labour markets."
        else:
            agri_text = f"⚠️ <strong>Moderate agricultural sector ({agri:.0f}%)</strong> — Balanced exposure. Both primary commodity and manufacturing tariffs have meaningful workforce effects."
        st.markdown(f'<div class="tw-panel"><p style="margin:0;font-size:0.9rem;line-height:1.6;">{agri_text}</p></div>', unsafe_allow_html=True)
    with col_v2:
        if age > 42:
            age_text = "👴 <strong>Aging workforce</strong> — Less adaptive to structural job displacement. Retraining is costly and slow. Pension systems under pressure as worker-to-retiree ratio falls."
        elif age < 32:
            age_text = "👶 <strong>Young workforce</strong> — High labour supply flexibility. Faster retraining capacity. But youth unemployment is acutely sensitive to trade-related job losses."
        else:
            age_text = "👨 <strong>Working-age peak</strong> — Standard adjustment trajectory. Moderate retraining feasibility. Demographic dividend still available if sector transitions are managed."
        st.markdown(f'<div class="tw-panel"><p style="margin:0;font-size:0.9rem;line-height:1.6;">{age_text}</p></div>', unsafe_allow_html=True)
    with st.expander("🎓 Teaching note: Demographics and trade vulnerability", expanded=False):
        st.markdown("Population pyramids show age structure; sector composition determines tariff exposure; dependency ratio describes dependants per working-age population.")

with forecast_tab:
    st.markdown("<h3 style='margin-bottom:1rem;'>🔮 Population Forecast & Demographic Scenario</h3>", unsafe_allow_html=True)
    hist_years, hist_pops, future_years, future_baseline, future_scenario = build_population_forecast(
        base_profile, years_ahead=forecast_years, fertility_adj=fertility_adj, migration_adj=migration_adj
    )
    fig_pop = go.Figure()
    fig_pop.add_trace(go.Scatter(x=hist_years, y=hist_pops, mode="lines+markers", name="Historical population", line=dict(color="#00d4ff", width=3)))
    fig_pop.add_trace(go.Scatter(x=future_years, y=future_baseline, mode="lines+markers", name="Baseline forecast", line=dict(color="#ff6b35", width=3, dash="dash")))
    if fertility_adj != 0.0 or migration_adj != 0:
        fig_pop.add_trace(go.Scatter(x=future_years, y=future_scenario, mode="lines+markers", name="Scenario forecast", line=dict(color="#43e97b", width=3)))
    fig_pop.update_layout(title=f"Population Trajectory — {country}", xaxis_title="Year", yaxis_title="Population (millions)", template="plotly_dark", height=380, uirevision=view_signature)
    st.plotly_chart(fig_pop, use_container_width=True, key=f"forecast_population_{view_signature}")

    col_s1, col_s2, col_s3 = st.columns(3, gap="medium")
    with col_s1:
        st.metric("Current population", f"{base_profile.get('population_mn', 0):,}M")
    with col_s2:
        st.metric(f"{forecast_years}-yr baseline", f"{round(future_baseline[-1], 1):,}M", delta=f"{round(future_baseline[-1] - base_profile.get('population_mn', 0), 1):+.1f}M")
    with col_s3:
        if fertility_adj != 0.0 or migration_adj != 0:
            st.metric(f"{forecast_years}-yr scenario", f"{round(future_scenario[-1], 1):,}M", delta=f"{round(future_scenario[-1] - future_baseline[-1], 1):+.1f}M vs baseline", delta_color="normal" if future_scenario[-1] >= future_baseline[-1] else "inverse")
        else:
            st.metric("Scenario", "No adjustment set", help="Use the sidebar sliders to set a fertility or migration scenario")

    st.divider()
    st.subheader("Sector workforce forecast")
    st.markdown(f"*Projected sector sizes under current trajectory — {country}*")
    base_labor = base_profile.get("labor_force_mn", 0)
    base_pop = base_profile.get("population_mn", 1)
    base_participation = (base_labor / base_pop * 100) if base_pop else 0
    sector_forecast_data = []
    for sector, key in [("Primary", "primary_sector_pct"), ("Secondary", "secondary_sector_pct"), ("Tertiary", "tertiary_sector_pct"), ("Quaternary", "quaternary_sector_pct")]:
        base_pct = base_profile.get(key, 0)
        current_mn = round(base_labor * base_pct / 100, 1)
        future_labor_base = future_baseline[-1] * base_participation / 100
        future_pct = base_pct + {"Primary": -0.5 * forecast_years / 5, "Secondary": 0.2 * forecast_years / 5, "Tertiary": 0.25 * forecast_years / 5, "Quaternary": 0.05 * forecast_years / 5}.get(sector, 0)
        future_pct = max(1, min(80, future_pct))
        future_mn = round(future_labor_base * future_pct / 100, 1)
        sector_forecast_data.append({"Sector": sector, "Current (%)": f"{base_pct}%", "Current (M workers)": current_mn, f"Forecast {2025 + forecast_years} (M workers)": future_mn, "Trend": "↓ Declining" if future_mn < current_mn else "↑ Growing"})
    st.dataframe(pd.DataFrame(sector_forecast_data), use_container_width=True, hide_index=True)
    with st.expander("🎓 Teaching note: The demographic transition model", expanded=False):
        st.markdown("The demographic transition model links falling mortality and fertility to changes in age structure, workforce supply, and sector composition. Migration can materially affect labour supply over the forecast horizon.")

with compare_tab:
    st.markdown("<h3 style='margin-bottom:1rem;'>🌍 Demographic Comparison</h3>", unsafe_allow_html=True)
    st.markdown(f"**{country} scenario ({scenario_year}) vs {compare_country} baseline**")
    comp_data = {
        "Indicator": ["Population (M)", "Labour Force (M)", "Median Age (yrs)", "Urbanisation (%)", "Primary Sector (%)", "Secondary Sector (%)", "Tertiary Sector (%)", "Quaternary Sector (%)", "GDP Growth (%)", "Inflation (%)"],
        country: [profile.get("population_mn", 0), profile.get("labor_force_mn", 0), profile.get("median_age", 0), profile.get("urbanization_pct", 0), profile.get("primary_sector_pct", 0), profile.get("secondary_sector_pct", 0), profile.get("tertiary_sector_pct", 0), profile.get("quaternary_sector_pct", 0), profile.get("gdp_growth", 0), profile.get("inflation", 0)],
        compare_country: [compare_profile.get("population_mn", 0), compare_profile.get("labor_force_mn", 0), compare_profile.get("median_age", 0), compare_profile.get("urbanization_pct", 0), compare_profile.get("primary_sector_pct", 0), compare_profile.get("secondary_sector_pct", 0), compare_profile.get("tertiary_sector_pct", 0), compare_profile.get("quaternary_sector_pct", 0), compare_profile.get("gdp_growth", 0), compare_profile.get("inflation", 0)],
    }
    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)
    st.markdown("<br/>", unsafe_allow_html=True)
    col_pyr1, col_pyr2 = st.columns(2, gap="large")
    with col_pyr1:
        st.plotly_chart(build_population_pyramid(profile, country), use_container_width=True, key=f"compare_pyramid_main_{view_signature}")
    with col_pyr2:
        st.plotly_chart(build_population_pyramid(compare_profile, compare_country), use_container_width=True, key=f"compare_pyramid_compare_{view_signature}")
    col_sec1, col_sec2 = st.columns(2, gap="large")
    with col_sec1:
        st.plotly_chart(build_sector_chart(profile, country), use_container_width=True, key=f"compare_sector_main_{view_signature}")
    with col_sec2:
        st.plotly_chart(build_sector_chart(compare_profile, compare_country), use_container_width=True, key=f"compare_sector_compare_{view_signature}")
    st.markdown("<br/>", unsafe_allow_html=True)
    phase_a, _, c_a, b_a = classify_demographic(profile)
    phase_b, _, c_b, b_b = classify_demographic(compare_profile)
    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">'
        f'<div class="tw-panel" style="border-left:4px solid {b_a};"><strong>{country}</strong><br/>{phase_a}</div>'
        f'<div class="tw-panel" style="border-left:4px solid {b_b};"><strong>{compare_country}</strong><br/>{phase_b}</div>'
        f'</div>', unsafe_allow_html=True,
    )
