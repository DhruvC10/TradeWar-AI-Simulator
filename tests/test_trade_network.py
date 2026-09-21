import pandas as pd

from trade_network import build_scenario_trade_network


def test_tariff_changes_targeted_trade_flow_and_metrics():
    _, baseline, _ = build_scenario_trade_network("China", "Electronics", 0, "US")
    _, shocked, _ = build_scenario_trade_network("China", "Electronics", 25, "US")

    base_china = baseline.loc[baseline["country"] == "China", "export_value_bn"].iloc[0]
    shock_china = shocked.loc[shocked["country"] == "China", "export_value_bn"].iloc[0]
    assert shock_china < base_china

    base_vietnam = baseline.loc[baseline["country"] == "Vietnam", "export_value_bn"].iloc[0]
    shock_vietnam = shocked.loc[shocked["country"] == "Vietnam", "export_value_bn"].iloc[0]
    assert shock_vietnam > base_vietnam

    assert not baseline["pagerank"].equals(shocked["pagerank"])
    assert not baseline["import_dependency"].equals(shocked["import_dependency"])
    assert not baseline["export_reach"].equals(shocked["export_reach"])


def test_tariff_reduction_moves_network_in_the_opposite_direction():
    _, baseline, _ = build_scenario_trade_network("China", "Electronics", 0, "US")
    _, relaxed, _ = build_scenario_trade_network("China", "Electronics", -25, "US")

    base_china = baseline.loc[baseline["country"] == "China", "export_value_bn"].iloc[0]
    relaxed_china = relaxed.loc[relaxed["country"] == "China", "export_value_bn"].iloc[0]
    assert relaxed_china > base_china

    base_vietnam = baseline.loc[baseline["country"] == "Vietnam", "export_value_bn"].iloc[0]
    relaxed_vietnam = relaxed.loc[relaxed["country"] == "Vietnam", "export_value_bn"].iloc[0]
    assert relaxed_vietnam < base_vietnam


def test_metrics_are_numeric_and_vulnerability_is_ranked():
    _, metrics, vulnerability = build_scenario_trade_network(
        "India", "Semiconductors", 20, "US"
    )
    assert isinstance(metrics, pd.DataFrame)
    assert len(metrics) == 10
    assert metrics[["pagerank", "import_dependency", "export_reach", "bridge_score"]].notna().all().all()
    assert len(vulnerability) == 10
    assert list(vulnerability.values()) == sorted(vulnerability.values(), reverse=True)
