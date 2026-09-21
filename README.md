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
