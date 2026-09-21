"""Tariff impact and beneficiary scoring.

The beneficiary model is continuous: tariff magnitude changes the size and
ranking of beneficiaries rather than crossing an arbitrary hard dollar cutoff.
"""
import numpy as np
import pandas as pd

TRADE_ELASTICITY = {"Electronics": -.8, "Semiconductors": -.9, "Machinery": -.7, "Chemicals": -.5, "Textiles": -.6, "Steel": -.7}
ALTERNATIVE_SUPPLIERS = {
    "China": ["Vietnam", "India", "Thailand", "Bangladesh"], "US": ["EU", "Japan", "South Korea"],
    "Vietnam": ["China", "Thailand", "Bangladesh", "India"], "India": ["Vietnam", "Bangladesh", "Thailand"],
    "Bangladesh": ["Vietnam", "India", "Thailand"], "Thailand": ["Vietnam", "India", "Bangladesh"],
    "Japan": ["South Korea", "Taiwan"], "South Korea": ["Japan", "Taiwan"], "Taiwan": ["South Korea", "Japan"], "EU": ["US", "Japan"],
}


def build_country_scenario(df, country, category, tariff_change_pct, target_partner, projection_horizon=3):
    elasticity = TRADE_ELASTICITY.get(category, -.7)
    base = float(df[(df.country == country) & (df.category == category) & (df.year == 2024)].export_value_bn_usd.sum())
    response = float(np.clip(elasticity * tariff_change_pct, -55, 55))
    horizon = 1 + max(0, projection_horizon - 1) * .08
    effective_change = response * horizon
    predicted = max(0, base * (1 + effective_change / 100))
    delta = predicted - base

    alternatives = ALTERNATIVE_SUPPLIERS.get(country, [])
    rows = []
    for other in sorted(df.country.unique()):
        baseline = float(df[(df.country == other) & (df.category == category) & (df.year == 2024)].export_value_bn_usd.sum())
        if other == country:
            pct = effective_change
        elif other in alternatives and tariff_change_pct > 0:
            pct = -.35 * effective_change
        elif other == target_partner and tariff_change_pct > 0:
            pct = .10 * abs(effective_change)
        elif other == target_partner and tariff_change_pct < 0:
            pct = -.04 * abs(effective_change)
        elif tariff_change_pct < 0 and other in alternatives:
            pct = .06 * effective_change
        else:
            pct = .02 * effective_change
        new_value = baseline * (1 + pct / 100)
        rows.append({"country": other, "baseline_export_bn": round(baseline, 2), "predicted_export_bn": round(new_value, 2), "change_pct": round(pct, 2), "change_bn": round(new_value - baseline, 2)})
    impact = pd.DataFrame(rows).sort_values("change_bn", ascending=False)

    scores = {}
    if tariff_change_pct > 0 and alternatives:
        pool = abs(delta) * np.clip(.30 + abs(tariff_change_pct) / 100 * .50, .30, .85)
        raw_weights = []
        for rank, alt in enumerate(alternatives):
            baseline = float(df[(df.country == alt) & (df.category == category) & (df.year == 2024)].export_value_bn_usd.sum())
            capacity = np.clip(.35 + baseline / max(base, 1) * .65, .35, 1.0)
            raw_weights.append((alt, (1 / (rank + 1)) * capacity))
        total = sum(weight for _, weight in raw_weights) or 1
        scores = {alt: pool * weight / total for alt, weight in raw_weights}
        beneficiary_type = "diversion"
    elif tariff_change_pct < 0:
        scores[country] = abs(delta) * .60
        if target_partner != country:
            scores[target_partner] = abs(delta) * .20
        for rank, alt in enumerate(alternatives[:3]):
            scores[alt] = abs(delta) * (.08 / (rank + 1))
        beneficiary_type = "gain"
    else:
        beneficiary_type = "none"

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    # Significance is relative to the scenario impact, not a fixed dollar cutoff.
    significance_floor = max(0.05, abs(delta) * 0.01)
    beneficiaries = [name for name, score in ranked if score >= significance_floor][:3]
    if tariff_change_pct == 0:
        beneficiary_status = "baseline"
    elif beneficiaries:
        beneficiary_status = "significant"
    else:
        beneficiary_status = "limited"

    return {
        "country": country, "category": category, "target_partner": target_partner,
        "baseline_export_bn": round(base, 2), "predicted_export_bn": round(predicted, 2),
        "trade_change_pct": round(effective_change, 2), "trade_delta_bn": round(delta, 2),
        "risk_score": round(min(100, 12 + abs(effective_change) * 1.6), 1),
        "trade_diversion": {k: round(v, 3) for k, v in scores.items()},
        "likely_beneficiaries": beneficiaries, "beneficiary_type": beneficiary_type,
        "beneficiary_status": beneficiary_status, "beneficiary_threshold_bn": round(significance_floor, 3),
        "impact_df": impact, "projection_horizon": projection_horizon,
    }
