"""Scenario-aware trade network calculations and visualization."""

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import ALTERNATIVE_SUPPLIERS, COUNTRIES, TRADE_ELASTICITY, TRADE_FLOWS
from theme import apply_plotly_theme, theme_colors

CATEGORY_ROUTE_MULTIPLIERS = {
    "Electronics": {"China": 1.20, "Taiwan": 1.35, "South Korea": 1.25, "Japan": 1.10, "Vietnam": 1.15, "India": 0.85},
    "Semiconductors": {"Taiwan": 1.45, "South Korea": 1.35, "Japan": 1.20, "China": 1.05, "US": 1.10, "India": 0.75},
    "Machinery": {"Japan": 1.30, "Germany": 1.0, "China": 1.15, "US": 1.20, "South Korea": 1.15, "EU": 1.15},
    "Chemicals": {"US": 1.20, "China": 1.15, "EU": 1.20, "Japan": 1.10, "India": 1.05},
    "Textiles": {"Bangladesh": 1.45, "Vietnam": 1.30, "India": 1.25, "China": 1.05, "Thailand": 1.10},
    "Steel": {"China": 1.30, "India": 1.15, "Japan": 1.15, "South Korea": 1.20, "EU": 1.10},
}


def _base_graph(category):
    graph = nx.DiGraph()
    graph.add_nodes_from(COUNTRIES)
    route_weights = CATEGORY_ROUTE_MULTIPLIERS.get(category, {})
    for exporter, importer, value in TRADE_FLOWS:
        graph.add_edge(exporter, importer, weight=round(float(value) * route_weights.get(exporter, 1.0), 2))
    return graph


def build_scenario_trade_network(country, category, tariff_change_pct, target_partner):
    graph = _base_graph(category)
    elasticity = abs(float(TRADE_ELASTICITY.get(category, -0.7)))
    shock = min(0.55, abs(float(tariff_change_pct)) / 100.0 * (0.65 + elasticity * 0.35))
    alternatives = ALTERNATIVE_SUPPLIERS.get(country, [])

    for exporter, importer in list(graph.edges()):
        weight = float(graph[exporter][importer]["weight"])
        if exporter == country and importer == target_partner:
            weight *= 1.0 - shock if tariff_change_pct > 0 else 1.0 + shock * 0.75
        elif exporter in alternatives and importer == target_partner:
            weight *= 1.0 + shock * 0.70 if tariff_change_pct > 0 else 1.0 - shock * 0.35
        graph[exporter][importer]["weight"] = max(1.0, round(weight, 2))

    metrics = _weighted_metrics(graph)
    return graph, metrics, _vulnerability(metrics)


def _weighted_metrics(graph):
    total_imports = {n: sum(d["weight"] for _, _, d in graph.in_edges(n, data=True)) for n in graph.nodes}
    total_exports = {n: sum(d["weight"] for _, _, d in graph.out_edges(n, data=True)) for n in graph.nodes}
    total_trade = sum(d["weight"] for _, _, d in graph.edges(data=True)) or 1.0
    pagerank = nx.pagerank(graph, weight="weight")
    distance_graph = graph.copy()
    for _, _, data in distance_graph.edges(data=True):
        data["distance"] = 1.0 / max(float(data["weight"]), 1.0)
    bridge = nx.betweenness_centrality(distance_graph, weight="distance", normalized=True)

    rows = []
    for country in COUNTRIES:
        rows.append({
            "country": country,
            "pagerank": round(pagerank[country], 4),
            "import_dependency": round(total_imports[country] / total_trade, 4),
            "export_reach": round(total_exports[country] / total_trade, 4),
            "bridge_score": round(bridge[country], 4),
            "import_value_bn": round(total_imports[country], 2),
            "export_value_bn": round(total_exports[country], 2),
        })
    return pd.DataFrame(rows).sort_values("pagerank", ascending=False).reset_index(drop=True)


def _vulnerability(metrics):
    by_country = metrics.set_index("country")
    return dict(sorted({
        country: round(100 * (
            0.45 * by_country.loc[country, "import_dependency"]
            + 0.30 * by_country.loc[country, "pagerank"]
            + 0.25 * by_country.loc[country, "bridge_score"]
        ), 3) for country in COUNTRIES
    }.items(), key=lambda item: item[1], reverse=True))


def build_network_figure(graph, metrics, title):
    """Create a stable interactive network that remains visible in both themes."""
    colors = theme_colors()
    background, text, border = colors["background"], colors["text"], colors["border"]

    # Keep the layout independent of trade volume so high-volume hubs cannot
    # collapse the graph into one unreadable cluster.
    positions = nx.spring_layout(graph, seed=42, k=3.0, iterations=300, weight=None)
    metric_map = metrics.set_index("country")
    pageranks = metrics["pagerank"]
    p_min, p_max = float(pageranks.min()), float(pageranks.max())
    span = max(p_max - p_min, 1e-6)

    edge_x, edge_y = [], []
    for exporter, importer in graph.edges():
        x0, y0 = positions[exporter]
        x1, y1 = positions[importer]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1.1, color="rgba(148,163,184,0.45)"),
        hoverinfo="none", showlegend=False,
    )

    node_x = [positions[c][0] for c in COUNTRIES]
    node_y = [positions[c][1] for c in COUNTRIES]
    sizes = [18 + 24 * ((metric_map.loc[c, "pagerank"] - p_min) / span) for c in COUNTRIES]
    hover = [
        f"<b>{c}</b><br>PageRank: {metric_map.loc[c, 'pagerank']:.4f}"
        f"<br>Import dependency: {metric_map.loc[c, 'import_dependency']:.2%}"
        f"<br>Export reach: {metric_map.loc[c, 'export_reach']:.2%}"
        f"<br>Bridge score: {metric_map.loc[c, 'bridge_score']:.4f}"
        f"<br>Exports: ${metric_map.loc[c, 'export_value_bn']:.1f}B"
        for c in COUNTRIES
    ]

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text", text=COUNTRIES,
        textposition="middle center", textfont=dict(size=11, color=text),
        hovertext=hover, hoverinfo="text", showlegend=False,
        marker=dict(
            size=sizes,
            color=[metric_map.loc[c, "pagerank"] for c in COUNTRIES],
            colorscale="Viridis", showscale=True,
            colorbar=dict(
                title=dict(text="PageRank", font=dict(color=text)),
                tickfont=dict(color=text), outlinecolor=border,
            ),
            line=dict(width=1, color=border),
        ),
    )

    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(
        title=dict(text=title, font=dict(color=text, size=22)),
        height=520,
        margin=dict(l=20, r=20, t=70, b=20),
        hovermode="closest",
        showlegend=False,
        paper_bgcolor=background,
        plot_bgcolor=background,
        font=dict(color=text),
        autosize=True,
        uirevision="trade-network",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
    )
    return apply_plotly_theme(fig)


def render_network_tab(*args):
    """Render the scenario network and support both current and legacy callers."""
    if len(args) == 4:
        country, category, tariff_change_pct, target_partner = args
    elif len(args) == 5:
        _, country, category, tariff_change_pct, target_partner = args
    else:
        raise TypeError("render_network_tab expects 4 or 5 arguments")

    graph, metrics, vulnerability = build_scenario_trade_network(country, category, tariff_change_pct, target_partner)
    st.caption("Illustrative category-weighted trade network. Tariff shocks alter the targeted route and alternative suppliers; values are model outputs, not observed bilateral trade statistics.")
    st.plotly_chart(
        build_network_figure(graph, metrics, f"{category} network — {country} ({tariff_change_pct:+.0f}%)"),
        use_container_width=True,
        config={"displaylogo": False, "responsive": True},
    )
    st.markdown("#### Scenario-adjusted trade network metrics")
    st.dataframe(metrics[["country", "pagerank", "import_dependency", "export_reach", "bridge_score", "import_value_bn", "export_value_bn"]], use_container_width=True, hide_index=True)
    st.markdown("#### Scenario-adjusted vulnerability")
    st.dataframe(pd.DataFrame(list(vulnerability.items()), columns=["Country", "Vulnerability"]), use_container_width=True, hide_index=True)
