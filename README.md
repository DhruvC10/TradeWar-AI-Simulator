# TradeWar AI Simulator

A Streamlit app for exploring how tariff shocks ripple through Asian supply chains.

## Author
Dhavin Shroff

## Features
- Interactive tariff scenario controls for exporters, products, and policy actors
- Forecast charts for historical and projected export behavior
- Country-by-country impact tables and visualizations
- Trade dependency network view for understanding supply-chain fragility
- Teaching-oriented explanations for tariff incidence, trade diversion, and spillovers

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

Optional AI tutor: copy [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) to `.streamlit/secrets.toml` and set `GEMINI_API_KEY`. Without it, the rest of the simulator still works.

## Deploy on Streamlit Community Cloud
1. Push this repository to GitHub (do not commit `env/`, `.env`, or `.streamlit/secrets.toml`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and create a new app pointing at the repo.
3. Set the **Main file path** to `app.py`.
4. Streamlit Cloud installs packages from `requirements.txt` and uses Python from `runtime.txt` (3.11).
5. Under **App settings → Secrets**, add (optional, for the AI tutor):
   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   ```
6. Deploy, then open the `*.streamlit.app` URL and smoke-test a few pages.

The simulator pages run without a Gemini key. The AI tutor is enabled only when `GEMINI_API_KEY` is set.

## Deploy on Railway
Packaging for Railway is in-repo: `Procfile`, `railway.toml`, and `.python-version` (3.11). See [RAILWAY_CHANGES_REQUIRED.md](RAILWAY_CHANGES_REQUIRED.md) for the full checklist.

1. Push this repository to GitHub (do not commit `env/`, `.env`, or `.streamlit/secrets.toml`).
2. In [Railway](https://railway.app), create a new project from that GitHub repo (root = repo root).
3. Confirm the start command (from `Procfile` / `railway.toml`):
   ```bash
   streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
   ```
4. Set Python to **3.11** (`.python-version` should be enough for Nixpacks; you can also set `NIXPACKS_PYTHON_VERSION=3.11` in Variables).
5. Optional Variables for the AI tutor:
   - `GEMINI_API_KEY` — enables the tutor
   - `GEMINI_MODEL` — override (default in code: `gemini-3.5-flash-lite`)
6. Prefer a health check on `/` with a **60–120s** start grace (first boot may call live World Bank / FX APIs).
7. Deploy, open the public URL, and smoke-test:
   - Home
   - Custom Scenario
   - One live-data page (e.g. Demographics or Financial Markets)
   - AI tutor (only if `GEMINI_API_KEY` is set)
