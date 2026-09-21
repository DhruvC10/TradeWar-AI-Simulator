import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import utils
from ai_tutor import render_global_chatbot
from beneficiary import build_country_scenario as continuous_build_country_scenario
from theme import inject_css
from utils import COUNTRY_PROFILES
from live_data import refresh_profiles, live_timestamp

utils.build_country_scenario = continuous_build_country_scenario
utils.inject_css = inject_css

st.set_page_config(page_title="TradeWar AI Simulator", page_icon="🌏", layout="wide", initial_sidebar_state="expanded")

try:
    live_profiles, live_years = refresh_profiles(COUNTRY_PROFILES)
    COUNTRY_PROFILES.update(live_profiles)
except Exception:
    live_years = {}


def render_visitor_counter():
    """Render a persistent, lightweight visit counter without affecting app state."""
    today_key = datetime.now().strftime("%Y-%m-%d")
    count_this_session = "1" if "visitor_counter_recorded" not in st.session_state else "0"
    st.session_state.setdefault("visitor_counter_recorded", True)

    components.html(
        f"""
        <div id="visitor-card" style="font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:0 0 18px 0;">
            <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                <div class="visitor-stat" style="border:1px solid rgba(128,128,128,.25);border-radius:10px;padding:10px 16px;min-width:150px;">
                    <div class="visitor-label" style="font-size:12px;opacity:.7;">🌍 Total Visits</div>
                    <div id="total-visits" style="font-size:24px;font-weight:700;margin-top:2px;">—</div>
                </div>
                <div class="visitor-stat" style="border:1px solid rgba(128,128,128,.25);border-radius:10px;padding:10px 16px;min-width:150px;">
                    <div class="visitor-label" style="font-size:12px;opacity:.7;">📅 Today's Visits</div>
                    <div id="today-visits" style="font-size:24px;font-weight:700;margin-top:2px;">—</div>
                </div>
            </div>
        </div>
        <script>
        (async function () {{
            const base = 'https://abacus.jasoncameron.dev';
            const totalKey = 'tradewar-ai-simulator-total-visits';
            const todayKey = 'tradewar-ai-simulator-visits-{today_key}';
            const shouldCount = {count_this_session};
            const card = document.getElementById('visitor-card');
            const stats = document.querySelectorAll('.visitor-stat');
            const labels = document.querySelectorAll('.visitor-label');
            const values = document.querySelectorAll('#total-visits, #today-visits');

            function firstNonEmpty(values) {{
                for (const value of values) {{
                    if (value && value.trim()) return value.trim();
                }}
                return '';
            }}

            function syncTheme() {{
                try {{
                    const parentDoc = window.parent.document;
                    const root = parentDoc.documentElement;
                    const body = parentDoc.body;
                    const app = parentDoc.querySelector('[data-testid="stApp"]') || parentDoc.querySelector('.stApp');
                    const appView = parentDoc.querySelector('[data-testid="stAppViewContainer"]');

                    const rootStyles = window.parent.getComputedStyle(root);
                    const bodyStyles = window.parent.getComputedStyle(body);
                    const appStyles = app ? window.parent.getComputedStyle(app) : null;
                    const appViewStyles = appView ? window.parent.getComputedStyle(appView) : null;

                    const text = firstNonEmpty([
                        rootStyles.getPropertyValue('--st-text-color'),
                        bodyStyles.getPropertyValue('--st-text-color'),
                        appStyles && appStyles.getPropertyValue('--st-text-color'),
                        appViewStyles && appViewStyles.getPropertyValue('--st-text-color')
                    ]);
                    const border = firstNonEmpty([
                        rootStyles.getPropertyValue('--st-border-color'),
                        bodyStyles.getPropertyValue('--st-border-color'),
                        appStyles && appStyles.getPropertyValue('--st-border-color'),
                        appViewStyles && appViewStyles.getPropertyValue('--st-border-color')
                    ]);
                    const muted = firstNonEmpty([
                        rootStyles.getPropertyValue('--st-gray-text-color'),
                        bodyStyles.getPropertyValue('--st-gray-text-color'),
                        appStyles && appStyles.getPropertyValue('--st-gray-text-color'),
                        appViewStyles && appViewStyles.getPropertyValue('--st-gray-text-color')
                    ]);
                    const background = firstNonEmpty([
                        rootStyles.getPropertyValue('--st-background-color'),
                        bodyStyles.getPropertyValue('--st-background-color'),
                        appStyles && appStyles.getPropertyValue('--st-background-color'),
                        appViewStyles && appViewStyles.getPropertyValue('--st-background-color')
                    ]);

                    const actualBackground = appViewStyles && appViewStyles.backgroundColor && appViewStyles.backgroundColor !== 'rgba(0, 0, 0, 0)'
                        ? appViewStyles.backgroundColor
                        : (appStyles && appStyles.backgroundColor && appStyles.backgroundColor !== 'rgba(0, 0, 0, 0)' ? appStyles.backgroundColor : bodyStyles.backgroundColor);
                    const actualText = appStyles && appStyles.color ? appStyles.color : bodyStyles.color;

                    if (text) {{
                        card.style.color = text;
                        values.forEach((el) => el.style.color = text);
                    }} else if (actualText) {{
                        card.style.color = actualText;
                        values.forEach((el) => el.style.color = actualText);
                    }}
                    if (border) stats.forEach((el) => el.style.borderColor = border);
                    if (muted) labels.forEach((el) => el.style.color = muted);
                    if (background) card.style.backgroundColor = background;

                    if (!text || !border || !muted || !background) {{
                        const rgb = actualBackground.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
                        if (rgb) {{
                            const luminance = (0.299 * Number(rgb[1]) + 0.587 * Number(rgb[2]) + 0.114 * Number(rgb[3])) / 255;
                            const fallbackText = luminance < 0.5 ? '#e5e7eb' : '#111827';
                            const fallbackMuted = luminance < 0.5 ? '#9ca3af' : '#64748b';
                            const fallbackBorder = luminance < 0.5 ? '#334155' : '#e2e8f0';
                            if (!text) {{ card.style.color = fallbackText; values.forEach((el) => el.style.color = fallbackText); }}
                            if (!muted) labels.forEach((el) => el.style.color = fallbackMuted);
                            if (!border) stats.forEach((el) => el.style.borderColor = fallbackBorder);
                        }}
                    }}
                }} catch (error) {{
                    console.debug('Visitor counter theme sync:', error);
                }}
            }}

            syncTheme();
            setInterval(syncTheme, 250);

            async function request(path) {{
                const response = await fetch(base + path, {{cache: 'no-store'}});
                if (!response.ok) throw new Error('Counter request failed: ' + response.status);
                return response.json();
            }}

            try {{
                const total = await request((shouldCount ? '/hit/' : '/get/') + 'tradewar-ai-simulator/visits');
                const today = await request((shouldCount ? '/hit/' : '/get/') + 'tradewar-ai-simulator/' + todayKey);

                const totalValue = total && typeof total.value !== 'undefined' ? total.value : total.count;
                const todayValue = today && typeof today.value !== 'undefined' ? today.value : today.count;

                document.getElementById('total-visits').textContent = Number(totalValue).toLocaleString();
                document.getElementById('today-visits').textContent = Number(todayValue).toLocaleString();
            }} catch (error) {{
                document.getElementById('total-visits').textContent = '—';
                document.getElementById('today-visits').textContent = '—';
                console.error('Visitor counter:', error);
            }}
        }})();
        </script>
        """,
        height=82,
        scrolling=False,
    )


def home():
    inject_css()
    st.sidebar.caption("**Author:** Dhavin Shroff")
    st.sidebar.caption("🌗 **Theme:** use ⋮ → Settings → Theme to switch between the configured light and dark themes.")
    st.sidebar.caption(f"🌐 Macro data refresh: {live_timestamp()}")

    st.markdown("""<div style="padding:2rem 0 1.5rem;border-bottom:1px solid var(--st-border-color);margin-bottom:2rem"><h1>🌏 TradeWar AI Simulator</h1><p style="max-width:720px;line-height:1.65">Explore how tariffs and trade shocks reshape supply chains, financial markets and demographics. Macro, demographic, FX and market inputs are refreshed from live public sources where available.</p></div>""", unsafe_allow_html=True)
    render_visitor_counter()
    cols = st.columns(6)
    cards = [
        ("⚙️", "Custom Scenario", "Model tariff changes and trade diversion.", "pages/1_Scenario.py"),
        ("🔬", "Historical Data Lab", "Upload real historical data, run statistics, forecasts and counterfactuals.", "pages/6_Historical_Data_Lab.py"),
        ("🔄", "Historical Counterfactual", "Explore alternative policy histories.", "pages/2_Historical_Counterfactual.py"),
        ("💹", "Financial Markets", "Track live market conditions and tariff scenarios.", "pages/3_Financial_Markets.py"),
        ("🌐", "Global Market Explorer", "Compare global indices, listed assets and any Yahoo Finance ticker.", "pages/5_Global_Market_Explorer.py"),
        ("👥", "Demographics", "Explore refreshed macro and demographic indicators.", "pages/4_Demographics.py"),
    ]
    for col, (icon, title, desc, page) in zip(cols, cards):
        with col:
            st.markdown(f'<div style="padding:1.2rem;border:1px solid var(--st-border-color);border-radius:.6rem;min-height:150px"><div style="font-size:1.4rem">{icon}</div><b>{title}</b><p style="font-size:.82rem;line-height:1.5">{desc}</p></div>', unsafe_allow_html=True)
            st.page_link(page, label="Open →", use_container_width=True)
    st.info("**Data note:** built-in trade-flow data remain synthetic for reproducible policy experiments. The Historical Data Lab lets users replace the synthetic dataset with real observations and clearly separates statistical/economic estimates from illustrative scenarios.")


pg = st.navigation({"": [st.Page(home, title="Home", icon="🏠", default=True)], "Simulator": [
    st.Page("pages/1_Scenario.py", title="Custom Scenario", icon="⚙️"),
    st.Page("pages/6_Historical_Data_Lab.py", title="Historical Data Lab", icon="🔬"),
    st.Page("pages/2_Historical_Counterfactual.py", title="Historical Counterfactual", icon="🔄"),
    st.Page("pages/3_Financial_Markets.py", title="Financial Markets", icon="💹"),
    st.Page("pages/5_Global_Market_Explorer.py", title="Global Market Explorer", icon="🌐"),
    st.Page("pages/4_Demographics.py", title="Demographics", icon="👥"),
]})
render_global_chatbot()
pg.run()
