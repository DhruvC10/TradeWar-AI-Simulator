import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from beneficiary import build_country_scenario
from trade_network import build_scenario_trade_network
from utils import (
    COUNTRY_PROFILES,
    build_policy_shock_summary,
    build_teaching_explanation,
    generate_trade_data,
)


def test_tariff_change_affects_scenario_output():
    df = generate_trade_data()
    scenario_up = build_country_scenario(df, "China", "Electronics", 25, "US")
    scenario_down = build_country_scenario(df, "China", "Electronics", -10, "US")

    assert scenario_up["trade_change_pct"] < 0
    assert scenario_down["trade_change_pct"] > 0
    assert scenario_up["predicted_export_bn"] < scenario_up["baseline_export_bn"]
    assert scenario_down["predicted_export_bn"] > scenario_down["baseline_export_bn"]

    impact = scenario_up["impact_df"]
    assert not impact.empty
    assert (impact["change_bn"] != 0).any()


def test_explanation_contains_economic_concept():
    df = generate_trade_data()
    scenario = build_country_scenario(df, "China", "Electronics", 25, "US")
    explanation = build_teaching_explanation(scenario, 25)
    text = " ".join(str(v) for v in explanation.values()).lower()
    assert "elasticity" in text or "trade diversion" in text
    assert "tariff" in text


def test_explanation_reflects_tariff_direction():
    df = generate_trade_data()
    scenario_up = build_country_scenario(df, "India", "Textiles", 15, "EU")
    scenario_down = build_country_scenario(df, "India", "Textiles", -10, "EU")
    explanation_up = build_teaching_explanation(scenario_up, 15)
    explanation_down = build_teaching_explanation(scenario_down, -10)
    text_up = " ".join(str(v) for v in explanation_up.values()).lower()
    text_down = " ".join(str(v) for v in explanation_down.values()).lower()

    assert "increase" in text_up or "higher" in text_up or "+" in explanation_up["mechanism"]
    assert "cut" in text_down or "reduce" in text_down or "-" in explanation_down["mechanism"]


def test_horizon_changes_scenario_projection():
    df = generate_trade_data()
    short_horizon = build_country_scenario(df, "China", "Electronics", 25, "US", projection_horizon=1)
    longer_horizon = build_country_scenario(df, "China", "Electronics", 25, "US", projection_horizon=5)

    assert short_horizon["predicted_export_bn"] != longer_horizon["predicted_export_bn"]


def test_scenario_network_changes_with_tariff():
    positive, _, _ = build_scenario_trade_network("China", "Electronics", 25, "US")
    negative, _, _ = build_scenario_trade_network("China", "Electronics", -10, "US")

    positive_weight = positive["China"]["US"]["weight"]
    negative_weight = negative["China"]["US"]["weight"]
    assert positive_weight != negative_weight


def test_country_profile_has_market_and_demographics():
    profile = COUNTRY_PROFILES["India"]
    assert "stock_ticker" in profile
    assert "age_distribution" in profile
    assert "currency" in profile
    assert "population_mn" in profile


def test_policy_shock_changes_scenario_outlook():
    base = build_policy_shock_summary("None", 0)
    shocked = build_policy_shock_summary("Post-9/11 US financial stabilization", 8)
    assert "No historical policy shock" in base
    assert "Historical scenario" in shocked
    assert "8%" in shocked or "-8%" in shocked or "+8%" in shocked
