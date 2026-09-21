import numpy as np
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from statsmodels.tsa.arima.model import ARIMA
from theme import apply_plotly_theme
try:
    import yfinance as yf
except Exception: yf = None
try:
    from live_data import refresh_profiles
except Exception: refresh_profiles = None
COUNTRIES=["China","India","Vietnam","Bangladesh","Thailand","South Korea","Taiwan","Japan","EU","US"]
CATEGORIES=["Electronics","Textiles","Semiconductors","Machinery","Chemicals","Steel"]
YEARS=list(range(2015,2025))
TRADE_ELASTICITY={"Electronics":-.8,"Semiconductors":-.9,"Machinery":-.7,"Chemicals":-.5,"Textiles":-.6,"Steel":-.7}
ALTERNATIVE_SUPPLIERS={"China":["Vietnam","India","Thailand","Bangladesh"],"US":["EU","Japan","South Korea"],"Vietnam":["China","Thailand","Bangladesh","India"],"India":["Vietnam","Bangladesh","Thailand"],"Bangladesh":["Vietnam","India","Thailand"],"Thailand":["Vietnam","India","Bangladesh"],"Japan":["South Korea","Taiwan"],"South Korea":["Japan","Taiwan"],"Taiwan":["South Korea","Japan"],"EU":["US","Japan"]}
TRADE_FLOWS=[("China","US",500),("China","EU",400),("China","Japan",170),("China","South Korea",160),("China","India",100),("China","Vietnam",80),("Vietnam","US",110),("Vietnam","EU",50),("Vietnam","China",70),("Vietnam","Japan",25),("India","US",80),("India","EU",65),("India","China",20),("South Korea","China",150),("South Korea","US",80),("Taiwan","China",180),("Taiwan","US",100),("Japan","US",150),("Japan","China",160),("Japan","EU",80),("US","EU",350),("US","Japan",80),("US","China",150),("Bangladesh","EU",20),("Bangladesh","US",10),("Thailand","US",45),("Thailand","China",40),("Thailand","EU",30)]
CATEGORY_TRADE_WEIGHTS={"Electronics":.30,"Semiconductors":.20,"Machinery":.18,"Chemicals":.12,"Textiles":.12,"Steel":.08}
CATEGORY_BILATERAL_MULTIPLIERS={}
COUNTRY_PROFILES={
"India":{"population_mn":1410,"urbanization_pct":36,"median_age":28,"gdp_growth":6.5,"inflation":4.8,"labor_force_mn":520,"primary_sector_pct":43,"secondary_sector_pct":25,"tertiary_sector_pct":28,"quaternary_sector_pct":4,"currency":"INR","currency_vs_usd":83.5,"stock_index":"NIFTY 50","stock_ticker":"^NSEI","market_cap_bn":4200,"age_distribution":{"0-14":26,"15-29":27,"30-44":22,"45-59":15,"60+":10}},
"China":{"population_mn":1411,"urbanization_pct":64,"median_age":39,"gdp_growth":5.2,"inflation":2.3,"labor_force_mn":770,"primary_sector_pct":23,"secondary_sector_pct":39,"tertiary_sector_pct":33,"quaternary_sector_pct":5,"currency":"CNY","currency_vs_usd":7.24,"stock_index":"SSE Composite","stock_ticker":"000001.SS","market_cap_bn":9800,"age_distribution":{"0-14":17,"15-29":19,"30-44":22,"45-59":22,"60+":20}},
"US":{"population_mn":335,"urbanization_pct":83,"median_age":38,"gdp_growth":2.5,"inflation":3.3,"labor_force_mn":165,"primary_sector_pct":1,"secondary_sector_pct":19,"tertiary_sector_pct":69,"quaternary_sector_pct":11,"currency":"USD","currency_vs_usd":1,"stock_index":"S&P 500","stock_ticker":"SPY","market_cap_bn":42000,"age_distribution":{"0-14":18,"15-29":20,"30-44":20,"45-59":19,"60+":23}},
"EU":{"population_mn":447,"urbanization_pct":75,"median_age":43,"gdp_growth":1.4,"inflation":2.9,"labor_force_mn":230,"primary_sector_pct":4,"secondary_sector_pct":25,"tertiary_sector_pct":63,"quaternary_sector_pct":8,"currency":"EUR","currency_vs_usd":.92,"stock_index":"Euro Stoxx 50","stock_ticker":"^STOXX50E","market_cap_bn":11000,"age_distribution":{"0-14":15,"15-29":17,"30-44":21,"45-59":22,"60+":25}},
"Vietnam":{"population_mn":99,"urbanization_pct":37,"median_age":32,"gdp_growth":7,"inflation":3.5,"labor_force_mn":56,"primary_sector_pct":38,"secondary_sector_pct":34,"tertiary_sector_pct":25,"quaternary_sector_pct":3,"currency":"VND","currency_vs_usd":24500,"stock_index":"VN-Index","stock_ticker":"^VNINDEX","market_cap_bn":260,"age_distribution":{"0-14":23,"15-29":26,"30-44":25,"45-59":17,"60+":9}},
"Bangladesh":{"population_mn":170,"urbanization_pct":29,"median_age":28,"gdp_growth":6,"inflation":5.2,"labor_force_mn":67,"primary_sector_pct":42,"secondary_sector_pct":28,"tertiary_sector_pct":27,"quaternary_sector_pct":3,"currency":"BDT","currency_vs_usd":110,"stock_index":"DSEX","stock_ticker":"DSEX.BD","market_cap_bn":45,"age_distribution":{"0-14":28,"15-29":29,"30-44":22,"45-59":13,"60+":8}},
"Japan":{"population_mn":123,"urbanization_pct":82,"median_age":49,"gdp_growth":1.9,"inflation":2.5,"labor_force_mn":75,"primary_sector_pct":2,"secondary_sector_pct":24,"tertiary_sector_pct":67,"quaternary_sector_pct":7,"currency":"JPY","currency_vs_usd":149,"stock_index":"Nikkei 225","stock_ticker":"^N225","market_cap_bn":6400,"age_distribution":{"0-14":12,"15-29":14,"30-44":19,"45-59":22,"60+":33}},
"South Korea":{"population_mn":52,"urbanization_pct":82,"median_age":42,"gdp_growth":2.6,"inflation":2.9,"labor_force_mn":28,"primary_sector_pct":4,"secondary_sector_pct":32,"tertiary_sector_pct":57,"quaternary_sector_pct":7,"currency":"KRW","currency_vs_usd":1320,"stock_index":"KOSPI","stock_ticker":"^KS11","market_cap_bn":1600,"age_distribution":{"0-14":12,"15-29":16,"30-44":22,"45-59":24,"60+":26}},
"Taiwan":{"population_mn":24,"urbanization_pct":81,"median_age":42,"gdp_growth":3.2,"inflation":2.4,"labor_force_mn":12,"primary_sector_pct":5,"secondary_sector_pct":36,"tertiary_sector_pct":53,"quaternary_sector_pct":6,"currency":"TWD","currency_vs_usd":31.8,"stock_index":"TAIEX","stock_ticker":"^TWII","market_cap_bn":1800,"age_distribution":{"0-14":13,"15-29":17,"30-44":22,"45-59":24,"60+":24}},
"Thailand":{"population_mn":71,"urbanization_pct":52,"median_age":40,"gdp_growth":2.5,"inflation":3.8,"labor_force_mn":38,"primary_sector_pct":31,"secondary_sector_pct":35,"tertiary_sector_pct":30,"quaternary_sector_pct":4,"currency":"THB","currency_vs_usd":35.5,"stock_index":"SET Index","stock_ticker":"^SET.BK","market_cap_bn":500,"age_distribution":{"0-14":17,"15-29":19,"30-44":25,"45-59":23,"60+":16}}}

def inject_css():
    st.markdown('''<style>.main .block-container{padding-top:2rem;padding-bottom:2rem}[data-testid="metric-container"]{padding:1.1rem;border-radius:.5rem}h1,h2,h3,h4,h5,h6{font-weight:600}</style>''',unsafe_allow_html=True)

def generate_trade_data():
    records=[]; base={"China":2500,"India":450,"Vietnam":280,"Bangladesh":45,"Thailand":250,"South Korea":600,"Taiwan":380,"Japan":700,"EU":2200,"US":1600}
    for y in YEARS:
        for c in COUNTRIES:
            for cat in CATEGORIES:
                v=base[c]*CATEGORY_TRADE_WEIGHTS[cat]*(1.04**(y-2015))*(.88 if y==2020 else 1)*np.random.uniform(.93,1.07)
                if y>=2018 and c in ["China","US"] and cat in ["Electronics","Semiconductors"]: v*=.82
                records.append({"year":y,"country":c,"category":cat,"export_value_bn_usd":round(v,2),"tariff_rate_pct":round(np.random.uniform(2,8),2)})
    return pd.DataFrame(records)

def build_trade_network():
    g=nx.DiGraph();g.add_nodes_from(COUNTRIES)
    for a,b,v in TRADE_FLOWS:g.add_edge(a,b,weight=v,label=f"${v}B")
    p=nx.pagerank(g,weight="weight");bc=nx.betweenness_centrality(g,weight="weight");ic=nx.in_degree_centrality(g);oc=nx.out_degree_centrality(g)
    m=pd.DataFrame({"country":COUNTRIES,"pagerank":[round(p.get(c,0),4) for c in COUNTRIES],"import_dependency":[round(ic.get(c,0),4) for c in COUNTRIES],"export_reach":[round(oc.get(c,0),4) for c in COUNTRIES],"bridge_score":[round(bc.get(c,0),4) for c in COUNTRIES]}).sort_values("pagerank",ascending=False)
    vuln={c:round(sum(g[u][c]["weight"] for u in g.predecessors(c))/1000*.5+bc.get(c,0)*30+p.get(c,0)*2,3) for c in COUNTRIES}
    return g,m,dict(sorted(vuln.items(),key=lambda x:-x[1]))

def forecast_series(series,steps=3):
    if len(series)<5:return np.array([series[-1]]*steps)
    try:return ARIMA(series,order=(1,1,1)).fit().forecast(steps=steps)
    except Exception:
        x=np.arange(len(series));c=np.polyfit(x,series,1);return np.array([c[1]+c[0]*(len(series)+i) for i in range(steps)])

def build_country_scenario(df,country,category,tariff_change_pct,target_partner,projection_horizon=3):
    e=TRADE_ELASTICITY.get(category,-.7);base=float(df[(df.country==country)&(df.category==category)&(df.year==2024)].export_value_bn_usd.sum());change=float(np.clip(e*tariff_change_pct,-55,55));factor=1+(projection_horizon-1)*.08;new=max(0,base*(1+change/100*factor));delta=new-base;alts=ALTERNATIVE_SUPPLIERS.get(country,[]);rows=[]
    for c in COUNTRIES:
        b=float(df[(df.country==c)&(df.category==category)&(df.year==2024)].export_value_bn_usd.sum())
        pct=change*factor if c==country else (-.4*change*factor if c in alts else (.12*abs(change)*factor if c==target_partner and tariff_change_pct>0 else -.05*abs(change)*factor if c==target_partner else .04*change*factor))
        rows.append({"country":c,"baseline_export_bn":round(b,2),"predicted_export_bn":round(b*(1+pct/100),2),"change_pct":round(pct,2),"change_bn":round(b*pct/100,2)})
    impact=pd.DataFrame(rows).sort_values("change_bn",ascending=False)
    scores={};pool=abs(delta)*min(.9,.35+abs(tariff_change_pct)/100*.45)
    if tariff_change_pct>0:
        weights=[1/(i+1) for i in range(len(alts))];total=sum(weights)
        for i,a in enumerate(alts):
            b=float(df[(df.country==a)&(df.category==category)&(df.year==2024)].export_value_bn_usd.sum());capacity=min(1,.35+b/max(base,1)*.65);scores[a]=pool*weights[i]/max(total,1)*capacity
        btype="diversion"
    elif tariff_change_pct<0:
        scores[country]=abs(delta)*.60
        if target_partner!=country:scores[target_partner]=abs(delta)*.20
        for i,a in enumerate(alts[:2]):scores[a]=abs(delta)*.08/(i+1)
        btype="gain"
    else:btype="none"
    beneficiaries=[k for k,v in sorted(scores.items(),key=lambda x:x[1],reverse=True) if v>.001][:3]
    status="significant" if beneficiaries else "limited"
    return {"country":country,"category":category,"target_partner":target_partner,"baseline_export_bn":round(base,2),"predicted_export_bn":round(new,2),"trade_change_pct":round(change,2),"trade_delta_bn":round(delta,2),"risk_score":round(min(100,abs(change)*1.6+12),1),"trade_diversion":{k:round(v,3) for k,v in scores.items()},"likely_beneficiaries":beneficiaries,"beneficiary_type":btype,"beneficiary_status":status,"impact_df":impact,"projection_horizon":projection_horizon,"elasticity":e}

def build_teaching_explanation(s,tariff):
    return {"concept":"Trade Elasticity + Trade Diversion" if tariff>0 else "Comparative Advantage + Market Access" if tariff<0 else "Baseline Equilibrium","concept_def":"The model estimates how tariff-driven price changes alter demand and redirect trade between suppliers.","mechanism":f"Tariff shock: {tariff:+.0f}%. Elasticity applied: {abs(TRADE_ELASTICITY.get(s['category'],-.7)):.1f}.","numbers":f"Exports: ${s['baseline_export_bn']:.1f}B → ${s['predicted_export_bn']:.1f}B ({s['trade_change_pct']:+.1f}%).","wider":f"Likely beneficiaries: {', '.join(s['likely_beneficiaries']) or 'None identified'}.","beginner":"A tariff makes one route relatively more or less attractive, so trade flows adjust.","key_terms":{"Tariff":"A tax on imports.","Trade diversion":"Trade moving to another supplier after a relative price change.","Comparative advantage":"Producing at a lower relative opportunity cost."}}

def render_teaching_panel(t):
    st.info(t["concept"])
    st.markdown(t["concept_def"])
    a,b=st.columns(2)
    a.markdown(f"**Mechanism**\n\n{t['mechanism']}")
    b.markdown(f"**Numbers**\n\n{t['numbers']}\n\n**Wider impact**\n\n{t['wider']}")

def build_forecast_chart(df,country,category,tariff_change_pct,steps=3):
    hist=df[(df.country==country)&(df.category==category)].sort_values('year');base=forecast_series(hist.export_value_bn_usd.values,steps);scenario=np.maximum(0,base*(1+TRADE_ELASTICITY.get(category,-.7)*tariff_change_pct/100));years=list(range(2025,2025+steps));fig=go.Figure();fig.add_trace(go.Scatter(x=hist.year,y=hist.export_value_bn_usd,mode='lines+markers',name='Historical'));fig.add_trace(go.Scatter(x=years,y=base,mode='lines+markers',name='Baseline'));fig.add_trace(go.Scatter(x=years,y=scenario,mode='lines+markers',name='Policy scenario'));return apply_plotly_theme(fig.update_layout(title=f'Export Trajectory — {country} | {category}',height=400)),base,scenario

def apply_policy_shock_to_scenario(s,event_name,shock_pct):
    if not event_name or event_name=='None':return s
    s['predicted_export_bn']=round(s['predicted_export_bn']*(1+shock_pct/100*.15),2);s['trade_delta_bn']=round(s['predicted_export_bn']-s['baseline_export_bn'],2);s['risk_score']=round(min(100,s['risk_score']+abs(shock_pct)*.7),1);return s

def build_policy_shock_summary(event_name,shock_pct):return 'No historical policy shock selected.' if not event_name or event_name=='None' else f'Historical scenario: {event_name}. Shock: {shock_pct:+.0f}%.'
def render_scenario_summary_metrics(s):
    a,b,c,d=st.columns(4);a.metric('Exporter',s['country']);b.metric('Category',s['category']);c.metric('Predicted export change',f"{s['trade_change_pct']:+.1f}%",delta=f"${s['trade_delta_bn']:+.1f}B");d.metric('Trade disruption risk',f"{s['risk_score']:.0f}/100")
def render_overview_tab(s,impact):
    st.dataframe(impact[['country','baseline_export_bn','predicted_export_bn','change_pct','change_bn']],use_container_width=True,hide_index=True)
    from theme import theme_colors
    tc=theme_colors()
    fig=px.bar(impact,x='country',y='change_bn',color='change_bn',color_continuous_scale=['#ef4444',tc['secondary'],'#10b981'],title=f"Trade Impact by Country — {s['country']} {s['category']}")
    fig.update_layout(height=420)
    st.plotly_chart(apply_plotly_theme(fig),use_container_width=True)
def render_forecast_tab(df,country,category,tariff,steps):
    fig,_,_=build_forecast_chart(df,country,category,tariff,steps);st.plotly_chart(fig,use_container_width=True)
def render_network_tab(G,country,category,tariff,target):
    from trade_network import build_scenario_trade_network, build_network_figure
    ng,metrics,vuln=build_scenario_trade_network(country,category,tariff,target)
    st.plotly_chart(build_network_figure(ng,metrics,f'{category} network — {country} ({tariff:+.0f}%)'),use_container_width=True)
    st.dataframe(metrics,use_container_width=True,hide_index=True)
    st.dataframe(pd.DataFrame(list(vuln.items()),columns=['Country','Vulnerability']),use_container_width=True,hide_index=True)
