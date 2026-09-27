"""
scoring.py
The prioritization engine.

Deliberately a transparent, explainable formula (not a black-box model) —
in a government context, officials and citizens need to be able to see
*why* a ward was ranked #1. The LLM layer (simulated here) is used only
for translation / clustering upstream, never for the ranking decision.
"""

import pandas as pd


def _normalize(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return series * 0 + 0.5
    return (series - lo) / (hi - lo)


def compute_ward_priority(wards_df: pd.DataFrame,
                           complaints_df: pd.DataFrame,
                           weights: dict | None = None) -> pd.DataFrame:
    """
    Combine per-ward complaint volume + urgency with population and the
    existing infrastructure gap into a single, explainable 0-100 score.

    weights keys: complaints, population, infra_gap, urgency
    (should sum to ~1.0; defaults reflect a public-interest-weighted mix)
    """
    weights = weights or {
        "complaints": 0.35,
        "population": 0.20,
        "infra_gap": 0.30,
        "urgency": 0.15,
    }

    agg = complaints_df.groupby("ward").agg(
        complaint_count=("complaint_id", "count"),
        avg_urgency=("urgency", "mean"),
        open_count=("status", lambda s: (~s.isin(["Resolved"])).sum()),
    ).reset_index()

    merged = wards_df.merge(agg, on="ward", how="left").fillna(
        {"complaint_count": 0, "avg_urgency": 0, "open_count": 0}
    )

    merged["infra_gap"] = 100 - merged["infra_index"]

    merged["n_complaints"] = _normalize(merged["complaint_count"])
    merged["n_population"] = _normalize(merged["population"])
    merged["n_infra_gap"] = _normalize(merged["infra_gap"])
    merged["n_urgency"] = _normalize(merged["avg_urgency"])

    merged["priority_score"] = round(100 * (
        weights["complaints"] * merged["n_complaints"] +
        weights["population"] * merged["n_population"] +
        weights["infra_gap"] * merged["n_infra_gap"] +
        weights["urgency"] * merged["n_urgency"]
    ), 1)

    merged["budget_per_capita"] = round(
        (merged["budget_allocated_lakh"] * 100000) / merged["population"], 1
    )

    merged = merged.sort_values("priority_score", ascending=False).reset_index(drop=True)
    merged.insert(0, "rank", merged.index + 1)

    # Human-readable "why" explanation for each ward — this is what makes
    # the recommendation auditable to a policymaker.
    def explain(row):
        reasons = []
        if row["n_complaints"] > 0.6:
            reasons.append(f"{int(row['complaint_count'])} citizen complaints (high volume)")
        if row["n_infra_gap"] > 0.6:
            reasons.append(f"low existing infrastructure (index {row['infra_index']}/100)")
        if row["n_population"] > 0.6:
            reasons.append(f"large population affected ({int(row['population']):,})")
        if row["n_urgency"] > 0.6:
            reasons.append(f"high average urgency ({row['avg_urgency']:.1f}/10)")
        if not reasons:
            reasons.append("moderate levels across all factors")
        return "; ".join(reasons)

    merged["why"] = merged.apply(explain, axis=1)

    cols = ["rank", "ward", "priority_score", "complaint_count", "open_count",
            "avg_urgency", "population", "infra_index", "budget_allocated_lakh",
            "budget_per_capita", "why"]
    return merged[cols]
