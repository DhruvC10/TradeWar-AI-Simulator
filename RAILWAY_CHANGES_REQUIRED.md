# Railway Deployment — Changes Required

## Current stage (summary)

TradeWar AI Simulator is a **feature-complete Streamlit multipage app** (Python 3.11) for tariff / supply-chain teaching scenarios. Core pages, synthetic trade data, live World Bank / FX / market adapters, and an optional Gemini AI tutor are implemented. CI runs `compileall` + pytest.

**Documented deploy target today:** Streamlit Community Cloud only (`README.md`, `runtime.txt`).

**Not Railway-ready out of the box:** no Dockerfile, Procfile, or `railway.toml`; Streamlit is hardcoded to port `8501` and does not bind `0.0.0.0` / `$PORT`.

| Area | Status |
|------|--------|
| App features | Ready (simulator works without Gemini) |
| Secrets model | Ready for env vars (`GEMINI_API_KEY` optional) |
| Database / volumes | Not required (stateless) |
| Railway packaging | Missing — changes below |

---

## Must-change (blocking)

### 1. Start command must use Railway `$PORT` and bind `0.0.0.0`

Railway routes traffic to the port in `$PORT`. The app currently assumes Streamlit’s default / config port **8501**.

**Add an explicit start command** (Railway service settings or `Procfile` / `railway.toml`):

```bash
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
```

Without this, the service will likely deploy but never become reachable.

### 2. Stop hardcoding port in `.streamlit/config.toml`

Current:

```toml
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = true
```

**Change:** remove `port = 8501` (or comment it out) so CLI / `$PORT` wins. Keep `headless = true`.

### 3. Add a Railway start artifact (pick one)

Choose one of:

| Option | What to add |
|--------|-------------|
| **A. Procfile** (simplest) | `web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true` |
| **B. railway.toml** | `[deploy] startCommand = "streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true"` |
| **C. Dockerfile** | `EXPOSE` + `CMD` using `$PORT`; set Python 3.11 base image |

Nixpacks alone is unreliable for Streamlit without an explicit start command.

### 4. Pin Python 3.11 for Railway

`runtime.txt` (`python-3.11`) is a **Streamlit Cloud** convention. Railway/Nixpacks may ignore it.

**Change (recommended):** set the Railway service Python version to **3.11**, or add a Dockerfile / Nixpacks config that installs 3.11 explicitly.

---

## Should-change (strongly recommended)

### 5. Railway environment variables

In the Railway project → Variables:

| Variable | Required | Notes |
|----------|----------|--------|
| `GEMINI_API_KEY` | No | Enables AI tutor; app runs without it |
| `GEMINI_MODEL` | No | Default in code: `gemini-3.5-flash-lite` |

No `secrets.toml` mount is required — `ai_tutor.py` falls back to `os.getenv`.

Do **not** commit `.streamlit/secrets.toml`.

### 6. Health check / start timeout

Home load calls live World Bank + FX refresh (parallel, short timeouts). Cold start after deploy can be slow.

**Recommendation:** health check on `/`, allow **60–120s** start/health grace so the first boot is not killed.

### 7. Outbound HTTPS

Allow egress to:

- World Bank API, Frankfurter FX
- Yahoo Finance / chart endpoints
- bdshare (DSE) when markets pages are used
- Google Gemini (if tutor enabled)
- Optional: Abacus visit counter (client-side)

No inbound DB or private network is needed.

### 8. Document Railway in `README.md`

Add a short “Deploy on Railway” section mirroring the Streamlit Cloud steps: start command, Python 3.11, optional `GEMINI_*` vars, smoke-test checklist.

---

## Nice-to-have (non-blocking)

| Item | Why |
|------|-----|
| `Dockerfile` | Reproducible builds; clearer than Nixpacks guessing |
| Lockfile (`uv.lock` / `pip freeze`) | Range pins in `requirements.txt` can drift |
| Exact version pins | Smaller surprise risk on rebuilds |
| Drop or gate Abacus iframe | Third-party; fails soft already |
| Raise / tune cold-start path | Defer `refresh_profiles` if health checks time out |

---

## What you do **not** need to change

- No database provisioning
- No persistent volume
- No Redis / session store (Streamlit session state is per instance)
- No change to page structure (`app.py` + `pages/`)
- Core simulator does not require Gemini
- No `packages.txt` / apt system packages required for a normal Linux wheel install

---

## Minimal Railway checklist

1. [x] Remove or override hardcoded `port = 8501` in `.streamlit/config.toml` *(Phase 1 done in repo)*
2. [x] Add Procfile **or** `railway.toml` **or** Dockerfile with start command using `$PORT` + `0.0.0.0` *(Phase 1: both Procfile + railway.toml)*
3. [x] Pin Python **3.11** in repo via `.python-version` *(Phase 1; still confirm on Railway service if needed)*
4. [ ] Connect repo; root = repo root; install via `requirements.txt` *(Phase 3 — manual)*
5. [ ] (Optional) Set `GEMINI_API_KEY` / `GEMINI_MODEL` *(Phase 3 — manual)*
6. [ ] Deploy; open public URL; smoke-test Home, Scenario, one live-data page, tutor if keyed *(Phase 4 — manual)*
7. [ ] If deploy fails health: increase start timeout; confirm process listens on `$PORT` *(Phase 4 — manual)*

---

## Suggested file diffs (implement later)

**`.streamlit/config.toml`** — remove port line:

```toml
[server]
headless = true
enableCORS = false
enableXsrfProtection = true
```

**`Procfile`** (new):

```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
```

**Optional `railway.toml`** (new):

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true"
restartPolicyType = "ON_FAILURE"
```

---

## Verdict

The project is **ready to run as a stateless Streamlit service** and is close to Railway-ready. Blocking work is packaging/runtime only: **respect `$PORT`, bind `0.0.0.0`, declare a start command, and use Python 3.11**. Optional Gemini env vars enable the tutor; nothing else is required for a first successful deploy.
