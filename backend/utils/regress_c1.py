import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

PROCESS_MEASURES = [
    "cognitive_load",
    "perceived_confusion",
    "trust_in_advice",
    "confidence",
    "ownership",
]
MANIPULATION_CHECKS = ["perceived_disagreement", "perceived_breadth"]


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL records from a specified path."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def build_dataframe(records: list[dict]) -> pd.DataFrame:
    """Extract valid survey records and create dummy variables."""
    rows = []
    for r in records:
        survey = r.get("simulated_survey")
        cond = r.get("condition")
        if not survey or "parse_error" in survey or not cond:
            continue
        row = {"profile_id": r.get("profile_id"), "condition": cond}
        ok = True
        for key in PROCESS_MEASURES + MANIPULATION_CHECKS:
            val = survey.get(key)
            if val is None or not isinstance(val, (int, float)):
                ok = False
                break
            row[key] = float(val)
        if ok:
            rows.append(row)
    df = pd.DataFrame(rows)
    df["C2_integrated"] = (df["condition"] == "integrated").astype(int)
    df["C3_competing"] = (df["condition"] == "competing").astype(int)
    return df


def run_two_step_ols(df: pd.DataFrame, dv: str) -> None:
    """Run two-step OLS regression for a specified dependent variable."""
    print("=" * 70)
    print(f"DV = {dv}")
    print("=" * 70)

    y = df[dv]

    # Step 1: baseline, condition only
    X1 = sm.add_constant(df[["C2_integrated", "C3_competing"]])
    m1 = sm.OLS(y, X1).fit()

    # Step 2: condition + process measures
    X2 = sm.add_constant(df[["C2_integrated", "C3_competing"] + PROCESS_MEASURES])
    m2 = sm.OLS(y, X2).fit()

    print(f"Step 1: {dv} ~ condition only")
    print(f"  R^2 = {m1.rsquared:.3f}")
    print(
        f"  C2_integrated: coef={m1.params['C2_integrated']:.3f}  p={m1.pvalues['C2_integrated']:.4f}"
    )
    print(
        f"  C3_competing:  coef={m1.params['C3_competing']:.3f}  p={m1.pvalues['C3_competing']:.4f}"
    )

    print(f"\nStep 2: {dv} ~ condition + process measures")
    print(
        f"  R^2 = {m2.rsquared:.3f}  (baseline: {m1.rsquared:.3f}, +{m2.rsquared - m1.rsquared:.3f})"
    )
    print(
        f"  C2_integrated: coef={m2.params['C2_integrated']:.3f}  p={m2.pvalues['C2_integrated']:.4f}"
        f"  (was {m1.params['C2_integrated']:.3f} in step 1)"
    )
    print(
        f"  C3_competing:  coef={m2.params['C3_competing']:.3f}  p={m2.pvalues['C3_competing']:.4f}"
        f"  (was {m1.params['C3_competing']:.3f} in step 1)"
    )
    print("\n  Process measure coefficients:")
    for pm in PROCESS_MEASURES:
        print(f"    {pm:<22} coef={m2.params[pm]:>7.3f}  p={m2.pvalues[pm]:.4f}")

    shrink_c2 = (
        abs(m2.params["C2_integrated"]) / abs(m1.params["C2_integrated"])
        if m1.params["C2_integrated"] != 0
        else float("nan")
    )
    shrink_c3 = (
        abs(m2.params["C3_competing"]) / abs(m1.params["C3_competing"])
        if m1.params["C3_competing"] != 0
        else float("nan")
    )
    print(f"\n  Condition coef retention ratio (step2/step1):")
    print(f"    C2_integrated: {shrink_c2 * 100:.0f}%")
    print(f"    C3_competing:  {shrink_c3 * 100:.0f}%\n")


def print_correlation_matrix(df: pd.DataFrame) -> None:
    """Print correlation matrix of process measures."""
    print("=" * 70)
    print("PROCESS MEASURES CORRELATION MATRIX")
    print("=" * 70)
    corr = df[PROCESS_MEASURES].corr()
    print(corr.round(2).to_string())
    print()


def print_vif(df: pd.DataFrame) -> None:
    """Calculate and display VIF for condition dummies and process measures."""
    print("=" * 70)
    print("VIF ANALYSIS")
    print("=" * 70)

    predictors = ["C2_integrated", "C3_competing"] + PROCESS_MEASURES
    X = sm.add_constant(df[predictors])

    rows = []
    for i, col in enumerate(X.columns):
        if col == "const":
            continue
        vif = variance_inflation_factor(X.values, i)
        rows.append((col, vif))

    print(f"{'variable':<24}{'VIF':>10}")
    print("-" * 34)
    for col, vif in rows:
        flag = ""
        if vif > 10:
            flag = "  <- Severe Multicollinearity (>10)"
        elif vif > 5:
            flag = "  <- Moderate Multicollinearity (>5)"
        print(f"{col:<24}{vif:>10.2f}{flag}")


def main():
    parser = argparse.ArgumentParser(
        description="Examine process measures and manipulation checks."
    )
    parser.add_argument("--input", required=True, help="Input JSONL file path")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    records = load_jsonl(input_path)
    df = build_dataframe(records)

    for dv in MANIPULATION_CHECKS:
        run_two_step_ols(df, dv)

    print_correlation_matrix(df)
    print_vif(df)


if __name__ == "__main__":
    main()
