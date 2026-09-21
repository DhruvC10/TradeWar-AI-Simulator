import pandas as pd
from beneficiary import build_country_scenario


def sample_data():
    rows = []
    values = {"China": 750, "Vietnam": 120, "India": 100, "Thailand": 80, "Bangladesh": 40, "US": 500, "EU": 450, "Japan": 250, "South Korea": 200, "Taiwan": 180}
    for country, value in values.items():
        rows.append({"year": 2024, "country": country, "category": "Electronics", "export_value_bn_usd": value, "tariff_rate_pct": 5})
    return pd.DataFrame(rows)


def test_negative_thirty_percent_has_beneficiaries():
    result = build_country_scenario(sample_data(), "China", "Electronics", -30, "US")
    assert result["likely_beneficiaries"]
    assert "China" in result["likely_beneficiaries"]
    assert result["beneficiary_status"] == "significant"


def test_positive_tariff_has_trade_diversion_beneficiaries():
    result = build_country_scenario(sample_data(), "China", "Electronics", 30, "US")
    assert result["beneficiary_type"] == "diversion"
    assert result["likely_beneficiaries"]
    assert result["beneficiary_status"] == "significant"


def test_beneficiary_score_changes_with_tariff_magnitude():
    data = sample_data()
    low = build_country_scenario(data, "China", "Electronics", 10, "US")
    high = build_country_scenario(data, "China", "Electronics", 30, "US")
    assert high["trade_delta_bn"] < low["trade_delta_bn"]
    assert sum(high["trade_diversion"].values()) > sum(low["trade_diversion"].values())


def test_zero_tariff_has_no_beneficiary_gain():
    result = build_country_scenario(sample_data(), "China", "Electronics", 0, "US")
    assert result["beneficiary_type"] == "none"
    assert result["beneficiary_status"] == "baseline"
    assert result["trade_delta_bn"] == 0
