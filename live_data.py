"""Live macroeconomic, demographic and FX data adapters."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import requests
import streamlit as st

WORLD_BANK_CODES={"India":"IND","China":"CHN","US":"USA","EU":"EUU","Vietnam":"VNM","Bangladesh":"BGD","Japan":"JPN","South Korea":"KOR","Taiwan":"TWN","Thailand":"THA"}
INDICATORS={"population_mn":"SP.POP.TOTL","urbanization_pct":"SP.URB.TOTL.IN.ZS","gdp_growth":"NY.GDP.MKTP.KD.ZG","inflation":"FP.CPI.TOTL.ZG","labor_force_mn":"SL.TLF.TOTL.IN","age_0_14":"SP.POP.0014.TO.ZS","age_15_64":"SP.POP.1564.TO.ZS","age_65_plus":"SP.POP.65UP.TO.ZS","agriculture_pct":"NV.AGR.TOTL.ZS","industry_pct":"NV.IND.TOTL.ZS","services_pct":"NV.SRV.TOTL.ZS"}

@st.cache_data(ttl=3600,show_spinner=False)
def _world_bank_indicator(country_code,indicator):
    try:
        r=requests.get(f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}",params={"format":"json","per_page":10},timeout=5);r.raise_for_status();payload=r.json()
        for row in payload[1] if len(payload)>1 else []:
            if row.get("value") is not None:return float(row["value"]),int(row["date"])
    except Exception:pass
    return None,None

@st.cache_data(ttl=900,show_spinner=False)
def get_live_fx_rate(base_currency,quote_currency="USD"):
    if base_currency==quote_currency:return 1.0
    try:
        r=requests.get(f"https://api.frankfurter.app/latest?from={base_currency}&to={quote_currency}",timeout=5);r.raise_for_status();return float(r.json()["rates"][quote_currency])
    except Exception:return None

@st.cache_data(ttl=3600,show_spinner=False)
def get_live_country_profile(country,fallback):
    code=WORLD_BANK_CODES.get(country);profile=dict(fallback)
    if not code:return profile,None
    values={};latest_year=None
    for key,indicator in INDICATORS.items():
        value,year=_world_bank_indicator(code,indicator)
        if value is not None:values[key]=value;latest_year=max(latest_year or year,year)
    if "population_mn" in values:profile["population_mn"]=round(values["population_mn"]/1e6,2)
    for key in ("urbanization_pct","gdp_growth","inflation"):
        if key in values:profile[key]=round(values[key],2)
    if "labor_force_mn" in values:profile["labor_force_mn"]=round(values["labor_force_mn"]/1e6,2)
    if all(k in values for k in ("age_0_14","age_15_64","age_65_plus")):
        working=values["age_15_64"];profile["age_distribution"]={"0-14":round(values["age_0_14"],1),"15-29":round(working*.47,1),"30-44":round(working*.35,1),"45-59":round(working*.18,1),"60+":round(values["age_65_plus"]+working*.05,1)}
        total=sum(profile["age_distribution"].values());profile["age_distribution"]["60+"]=round(profile["age_distribution"]["60+"]+100-total,1)
    if "agriculture_pct" in values:profile["primary_sector_pct"]=round(values["agriculture_pct"],1)
    if "industry_pct" in values:profile["secondary_sector_pct"]=round(values["industry_pct"],1)
    if "services_pct" in values:
        profile["tertiary_sector_pct"]=round(values["services_pct"],1)
        if all(k in values for k in ("agriculture_pct","industry_pct")):profile["quaternary_sector_pct"]=max(0,round(100-values["agriculture_pct"]-values["industry_pct"]-values["services_pct"],1))
    currency=profile.get("currency")
    fx=get_live_fx_rate(currency,"USD") if currency else None
    if fx is not None:profile["currency_vs_usd"]=round(1/fx,6) if currency!="USD" else 1.0
    profile["live_data_year"]=latest_year
    profile["fx_live"]=fx is not None
    return profile,latest_year

def refresh_profiles(profiles):
    refreshed,years={},{}
    # API calls are independent. Parallelism keeps first-load latency bounded
    # while each endpoint remains cached for subsequent Streamlit reruns.
    with ThreadPoolExecutor(max_workers=min(8,len(profiles))) as executor:
        futures={executor.submit(get_live_country_profile,country,fallback):country for country,fallback in profiles.items()}
        for future in as_completed(futures):
            country=futures[future]
            try:refreshed[country],years[country]=future.result()
            except Exception:refreshed[country],years[country]=dict(profiles[country]),None
    return refreshed,years

def live_timestamp():return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
