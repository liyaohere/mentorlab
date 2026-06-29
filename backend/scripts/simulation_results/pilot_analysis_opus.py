#!/usr/bin/env python3
"""
Pilot Simulation Statistics — Run 004 (Claude Opus, both test types)
Extracts all statistics needed for the pilot results section.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

# ── Config ──────────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).parent / "runs" / "run004_20260406_opus_both.jsonl"
OUTPUT_FILE = Path(__file__).parent / "pilot_statistics_opus.json"

# Anthropic Opus pricing (per 1M tokens)
PRICE_INPUT_PER_M = 15.00
PRICE_OUTPUT_PER_M = 75.00

SURVEY_ITEMS = [
    "cognitive_load",
    "perceived_confusion",
    "trust_in_advice",
    "confidence",
    "ownership",
    "perceived_disagreement",
    "perceived_breadth",
]

CONDITIONS = ["single", "integrated", "competing"]

# ── Load data ───────────────────────────────────────────────────────────
records = []
with open(DATA_FILE) as f:
    for line in f:
        records.append(json.loads(line.strip()))

print(f"Total records loaded: {len(records)}")
print("=" * 80)


# ── Helpers ─────────────────────────────────────────────────────────────
def word_count(text):
    """Count words in a string."""
    if not text:
        return 0
    return len(text.split())


def get_shown_text(shown):
    """Return the full text of 'shown', joining list items if needed."""
    if isinstance(shown, list):
        return " ".join(shown)
    return shown or ""


def get_shown_word_count(shown):
    """Word count for shown field (string or list)."""
    return word_count(get_shown_text(shown))


def check_format_compliance(shown):
    """Check if CAUSE:, PREDICTION:, NEXT STEP: are present."""
    if isinstance(shown, list):
        texts = shown
    else:
        texts = [shown] if shown else []

    has_cause = any("CAUSE:" in (t or "") for t in texts)
    has_prediction = any("PREDICTION:" in (t or "") for t in texts)
    has_next_step = any("NEXT STEP:" in (t or "") for t in texts)
    return has_cause and has_prediction and has_next_step


def fmt(val, decimals=2):
    """Format a number."""
    if isinstance(val, (int, np.integer)):
        return int(val)
    return round(float(val), decimals)


def fmt_p(p_val):
    """Format p-value: use scientific notation for very small values."""
    if p_val < 0.0001:
        return f"{p_val:.2e}"
    return f"{p_val:.4f}"


def kruskal_test(groups):
    """Run Kruskal-Wallis test, return H-statistic and p-value."""
    valid = [g for g in groups if len(g) > 0]
    if len(valid) < 2:
        return None, None
    h_stat, p_val = stats.kruskal(*valid)
    return fmt(h_stat, 3), fmt_p(p_val)


# ── Split by test_type ──────────────────────────────────────────────────
subsets = {"across": [], "within": []}
for rec in records:
    subsets[rec["test_type"]].append(rec)


# ── Main analysis function ──────────────────────────────────────────────
def analyze_subset(data, label):
    """Run all analyses on a subset of data. Returns dict of results."""
    results = {}
    print(f"\n{'#' * 80}")
    print(f"# {label.upper()} SUBJECT DATA (test_type = '{label}')")
    print(f"{'#' * 80}")

    # Group by condition
    by_cond = defaultdict(list)
    for rec in data:
        by_cond[rec["condition"]].append(rec)

    # ── 1. Sample sizes ────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("1. SAMPLE SIZES PER CONDITION")
    print(f"{'─' * 60}")
    sample_sizes = {}
    # Count error records (those missing 'result' key or with non-empty errors)
    error_ids = []
    for rec in data:
        if "result" not in rec or rec.get("result") is None:
            error_ids.append(rec.get("run_id", "unknown"))
    if error_ids:
        print(
            f"  NOTE: {len(error_ids)} record(s) have no result and are excluded "
            f"from content analyses: {error_ids}"
        )

    for c in CONDITIONS:
        n = len(by_cond[c])
        sample_sizes[c] = n
        print(f"  {c:12s}: N = {n}")
    print(f"  {'TOTAL':12s}: N = {sum(sample_sizes.values())}")
    results["sample_sizes"] = sample_sizes

    # Helper: filter records that have a valid result
    def has_result(rec):
        return (
            "result" in rec
            and rec["result"] is not None
            and "shown" in rec.get("result", {})
        )

    # ── 2. Word counts of AI output ────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("2. WORD COUNTS OF AI OUTPUT (result.shown)")
    print(f"{'─' * 60}")
    wc_results = {}
    wc_groups = {}
    for c in CONDITIONS:
        wcs = [
            get_shown_word_count(rec["result"]["shown"])
            for rec in by_cond[c]
            if has_result(rec)
        ]
        wc_groups[c] = wcs
        stats_dict = {
            "mean": fmt(np.mean(wcs)),
            "sd": fmt(np.std(wcs, ddof=1)),
            "min": fmt(np.min(wcs)),
            "max": fmt(np.max(wcs)),
        }
        wc_results[c] = stats_dict
        print(
            f"  {c:12s}: M = {stats_dict['mean']}, SD = {stats_dict['sd']}, "
            f"range = [{stats_dict['min']}, {stats_dict['max']}]"
        )

    h, p = kruskal_test([wc_groups[c] for c in CONDITIONS])
    wc_results["kruskal_wallis"] = {"H": h, "p": str(p)}
    print(f"  Kruskal-Wallis: H = {h}, p = {p}")
    # Also pairwise for word counts
    print("  Pairwise Mann-Whitney U:")
    for c1, c2 in [
        ("single", "integrated"),
        ("single", "competing"),
        ("integrated", "competing"),
    ]:
        if wc_groups[c1] and wc_groups[c2]:
            u, pv = stats.mannwhitneyu(
                wc_groups[c1], wc_groups[c2], alternative="two-sided"
            )
            print(f"    {c1} vs {c2}: U = {u:.1f}, p = {fmt_p(pv)}")
    results["ai_output_word_counts"] = wc_results

    # ── 3. Format compliance ───────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("3. FORMAT COMPLIANCE (CAUSE / PREDICTION / NEXT STEP)")
    print(f"{'─' * 60}")
    compliance_results = {}
    for c in CONDITIONS:
        valid_recs = [rec for rec in by_cond[c] if has_result(rec)]
        compliant = sum(
            1 for rec in valid_recs if check_format_compliance(rec["result"]["shown"])
        )
        total = len(valid_recs)
        pct = fmt(100 * compliant / total if total > 0 else 0, 1)
        compliance_results[c] = {"compliant": compliant, "total": total, "pct": pct}
        print(f"  {c:12s}: {compliant}/{total} = {pct}%")
    results["format_compliance"] = compliance_results

    # ── 4. Divergence check pass rate ──────────────────────────────────
    print(f"\n{'─' * 60}")
    print("4. DIVERGENCE CHECK PASS RATE (integrated & competing only)")
    print(f"{'─' * 60}")
    div_results = {}
    for c in ["integrated", "competing"]:
        recs = [rec for rec in by_cond[c] if has_result(rec)]
        checks = [rec["result"].get("divergence_check") for rec in recs]
        n_pass = sum(1 for ch in checks if ch == "PASS")
        n_fail = sum(1 for ch in checks if ch and ch.startswith("FAIL"))
        n_null = sum(1 for ch in checks if ch is None)
        total = len(checks)
        pass_rate = fmt(100 * n_pass / total if total > 0 else 0, 1)
        div_results[c] = {
            "pass": n_pass,
            "fail": n_fail,
            "null": n_null,
            "total": total,
            "pass_rate_pct": pass_rate,
        }
        print(
            f"  {c:12s}: PASS = {n_pass}, FAIL = {n_fail}, null = {n_null} "
            f"→ pass rate = {pass_rate}%"
        )
    results["divergence_check"] = div_results

    # ── 5. Simulated survey scores ─────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("5. SIMULATED SURVEY SCORES (1–7 Likert)")
    print(f"{'─' * 60}")
    survey_results = {}
    for item in SURVEY_ITEMS:
        item_data = {}
        groups = []
        print(f"\n  {item}:")
        for c in CONDITIONS:
            vals = [
                rec["simulated_survey"][item]
                for rec in by_cond[c]
                if rec.get("simulated_survey") and item in rec["simulated_survey"]
            ]
            groups.append(vals)
            m = fmt(np.mean(vals))
            sd = fmt(np.std(vals, ddof=1))
            item_data[c] = {"mean": m, "sd": sd, "n": len(vals)}
            print(f"    {c:12s}: M = {m}, SD = {sd} (n = {len(vals)})")

        # Kruskal-Wallis for key manipulation check items
        if item in (
            "perceived_disagreement",
            "perceived_breadth",
            "cognitive_load",
            "perceived_confusion",
            "trust_in_advice",
            "confidence",
            "ownership",
        ):
            h, p = kruskal_test(groups)
            item_data["kruskal_wallis"] = {"H": h, "p": p}
            print(f"    Kruskal-Wallis: H = {h}, p = {p}")

        survey_results[item] = item_data
    results["survey_scores"] = survey_results

    # ── 6. Response word counts ────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("6. RESPONSE WORD COUNTS (simulated_response)")
    print(f"{'─' * 60}")
    resp_wc_results = {}
    for c in CONDITIONS:
        wcs = [
            word_count(rec.get("simulated_response", ""))
            for rec in by_cond[c]
            if rec.get("simulated_response")
        ]
        m = fmt(np.mean(wcs))
        sd = fmt(np.std(wcs, ddof=1))
        resp_wc_results[c] = {"mean": m, "sd": sd}
        print(f"  {c:12s}: M = {m}, SD = {sd}")
    results["response_word_counts"] = resp_wc_results

    # ── 7. Token usage and cost ────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("7. TOKEN USAGE AND COST")
    print(f"{'─' * 60}")
    token_results = {}
    for c in CONDITIONS:
        valid_tok = [rec for rec in by_cond[c] if "total_input_tokens" in rec]
        inp_tokens = [rec["total_input_tokens"] for rec in valid_tok]
        out_tokens = [rec["total_output_tokens"] for rec in valid_tok]
        wall_secs = [rec["wall_clock_seconds"] for rec in valid_tok]

        # Cost per run
        costs = [
            (it / 1_000_000) * PRICE_INPUT_PER_M + (ot / 1_000_000) * PRICE_OUTPUT_PER_M
            for it, ot in zip(inp_tokens, out_tokens)
        ]

        stats_dict = {
            "mean_input_tokens": fmt(np.mean(inp_tokens), 0),
            "mean_output_tokens": fmt(np.mean(out_tokens), 0),
            "mean_wall_seconds": fmt(np.mean(wall_secs), 1),
            "mean_cost_usd": fmt(np.mean(costs), 4),
            "total_cost_usd": fmt(np.sum(costs), 4),
        }
        token_results[c] = stats_dict
        print(
            f"  {c:12s}: input = {stats_dict['mean_input_tokens']:>7} tok, "
            f"output = {stats_dict['mean_output_tokens']:>6} tok, "
            f"wall = {stats_dict['mean_wall_seconds']:>5}s, "
            f"cost/run = ${stats_dict['mean_cost_usd']:.4f}, "
            f"total = ${stats_dict['total_cost_usd']:.4f}"
        )

    # Overall totals
    all_inp = sum(rec.get("total_input_tokens", 0) for rec in data)
    all_out = sum(rec.get("total_output_tokens", 0) for rec in data)
    total_cost = (all_inp / 1_000_000) * PRICE_INPUT_PER_M + (
        all_out / 1_000_000
    ) * PRICE_OUTPUT_PER_M
    token_results["overall"] = {
        "total_input_tokens": all_inp,
        "total_output_tokens": all_out,
        "total_cost_usd": fmt(total_cost, 4),
        "mean_cost_per_run_usd": fmt(total_cost / len(data), 4),
    }
    print(
        f"\n  OVERALL: {all_inp} input tok, {all_out} output tok, "
        f"total cost = ${total_cost:.4f}, mean/run = ${total_cost / len(data):.4f}"
    )
    results["token_usage"] = token_results

    # ── 8. Pipeline reliability ────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("8. PIPELINE RELIABILITY")
    print(f"{'─' * 60}")
    total_runs = len(data)
    error_runs = sum(
        1
        for rec in data
        if (rec.get("errors") and len(rec["errors"]) > 0)
        or "result" not in rec
        or rec.get("result") is None
    )
    success_runs = total_runs - error_runs
    reliability_results = {
        "total_runs": total_runs,
        "successful_runs": success_runs,
        "error_runs": error_runs,
        "success_rate_pct": fmt(
            100 * success_runs / total_runs if total_runs > 0 else 0, 1
        ),
    }
    results["pipeline_reliability"] = reliability_results
    print(f"  Total runs:      {total_runs}")
    print(f"  Successful runs: {success_runs}")
    print(f"  Error runs:      {error_runs}")
    print(f"  Success rate:    {reliability_results['success_rate_pct']}%")

    if error_runs > 0:
        print("\n  Error details:")
        for rec in data:
            has_err = rec.get("errors") and len(rec["errors"]) > 0
            missing_result = "result" not in rec or rec.get("result") is None
            if has_err or missing_result:
                errs = rec.get("errors", [])
                reason = (
                    f"errors={errs}" if has_err else "missing result (pipeline failure)"
                )
                print(f"    {rec.get('run_id', 'unknown')}: {reason}")

    return results


# ── Run analysis for both subsets ───────────────────────────────────────
all_results = {}
all_results["across_subject"] = analyze_subset(subsets["across"], "across")
all_results["within_subject"] = analyze_subset(subsets["within"], "within")

# ── 9. Within-subject: profile-level comparison table ───────────────────
print(f"\n{'#' * 80}")
print("# 9. WITHIN-SUBJECT: PER-PROFILE SURVEY SCORES (Manipulation Check Table)")
print(f"{'#' * 80}")

within_data = subsets["within"]
profiles = sorted(set(rec["profile_id"] for rec in within_data))

# Build lookup: (profile_id, condition) -> survey
profile_lookup = {}
for rec in within_data:
    profile_lookup[(rec["profile_id"], rec["condition"])] = rec.get(
        "simulated_survey", {}
    )

# Print header
header = f"{'Profile':8s}"
for item in SURVEY_ITEMS:
    abbrev = item[:6]
    header += f" | {abbrev:>6s}(S) {abbrev:>6s}(I) {abbrev:>6s}(C)"
# Simplified table: one row per profile, columns = items x conditions
print(f"\n{'─' * 60}")
print("Per-profile survey scores (S=single, I=integrated, C=competing)")
print(f"{'─' * 60}")

# Print item by item for readability
within_profile_table = {}
for pid in profiles:
    row = {}
    for item in SURVEY_ITEMS:
        row[item] = {}
        for c in CONDITIONS:
            val = profile_lookup.get((pid, c), {}).get(item, None)
            row[item][c] = val
    within_profile_table[pid] = row

# Print as a readable table per item
for item in SURVEY_ITEMS:
    print(f"\n  {item}:")
    print(
        f"    {'Profile':8s}  {'single':>8s}  {'integrated':>11s}  {'competing':>10s}  {'C-S diff':>8s}"
    )
    diffs = []
    for pid in profiles:
        vals = within_profile_table[pid][item]
        s_val = vals.get("single", "-")
        i_val = vals.get("integrated", "-")
        c_val = vals.get("competing", "-")
        diff = ""
        if isinstance(c_val, (int, float)) and isinstance(s_val, (int, float)):
            d = c_val - s_val
            diff = f"{d:+d}" if isinstance(d, int) else f"{d:+.1f}"
            diffs.append(d)
        print(
            f"    {pid:8s}  {str(s_val):>8s}  {str(i_val):>11s}  {str(c_val):>10s}  {diff:>8s}"
        )
    if diffs:
        print(
            f"    {'Mean':8s}  {'':>8s}  {'':>11s}  {'':>10s}  {np.mean(diffs):>+8.2f}"
        )

all_results["within_profile_table"] = within_profile_table

# ── Pairwise comparisons for key manipulation checks (across-subject) ──
print(f"\n{'#' * 80}")
print("# PAIRWISE COMPARISONS (across-subject, Mann-Whitney U)")
print(f"{'#' * 80}")

across_by_cond = defaultdict(list)
for rec in subsets["across"]:
    across_by_cond[rec["condition"]].append(rec)

pairwise_results = {}
for item in ["perceived_disagreement", "perceived_breadth", "cognitive_load"]:
    print(f"\n  {item}:")
    pairs = [
        ("single", "integrated"),
        ("single", "competing"),
        ("integrated", "competing"),
    ]
    item_pairs = {}
    for c1, c2 in pairs:
        v1 = [
            rec["simulated_survey"][item]
            for rec in across_by_cond[c1]
            if rec.get("simulated_survey") and item in rec.get("simulated_survey", {})
        ]
        v2 = [
            rec["simulated_survey"][item]
            for rec in across_by_cond[c2]
            if rec.get("simulated_survey") and item in rec.get("simulated_survey", {})
        ]
        u_stat, p_val = stats.mannwhitneyu(v1, v2, alternative="two-sided")
        # Effect size: rank-biserial r = 1 - 2U / (n1 * n2)
        n1, n2 = len(v1), len(v2)
        r_rb = 1 - (2 * u_stat) / (n1 * n2)
        item_pairs[f"{c1}_vs_{c2}"] = {
            "U": fmt(u_stat, 1),
            "p": fmt_p(p_val),
            "r_rank_biserial": fmt(r_rb, 3),
            "n1": n1,
            "n2": n2,
            "mean1": fmt(np.mean(v1)),
            "mean2": fmt(np.mean(v2)),
        }
        print(
            f"    {c1} vs {c2}: U = {u_stat:.1f}, p = {fmt_p(p_val)}, "
            f"r_rb = {r_rb:.3f} (M1 = {np.mean(v1):.2f}, M2 = {np.mean(v2):.2f})"
        )
    pairwise_results[item] = item_pairs

all_results["pairwise_comparisons_across"] = pairwise_results

# ── Summary statistics for paper ────────────────────────────────────────
print(f"\n{'#' * 80}")
print("# SUMMARY FOR PAPER")
print(f"{'#' * 80}")

across = all_results["across_subject"]
print(
    f"\nAcross-subject N: {sum(across['sample_sizes'].values())} "
    f"(single={across['sample_sizes']['single']}, "
    f"integrated={across['sample_sizes']['integrated']}, "
    f"competing={across['sample_sizes']['competing']})"
)
print(f"Pipeline success rate: {across['pipeline_reliability']['success_rate_pct']}%")
print(
    f"Format compliance: "
    f"single={across['format_compliance']['single']['pct']}%, "
    f"integrated={across['format_compliance']['integrated']['pct']}%, "
    f"competing={across['format_compliance']['competing']['pct']}%"
)
print(
    f"Divergence pass rate: "
    f"integrated={across['divergence_check']['integrated']['pass_rate_pct']}%, "
    f"competing={across['divergence_check']['competing']['pass_rate_pct']}%"
)

print(f"\nKey manipulation checks (across-subject):")
for item in ["perceived_disagreement", "perceived_breadth", "cognitive_load"]:
    ss = across["survey_scores"][item]
    kw = ss.get("kruskal_wallis", {})
    print(
        f"  {item}: "
        f"single M={ss['single']['mean']}, "
        f"integrated M={ss['integrated']['mean']}, "
        f"competing M={ss['competing']['mean']} | "
        f"H={kw.get('H')}, p={kw.get('p')}"
    )


# ── Save results ────────────────────────────────────────────────────────
# Convert numpy types for JSON serialization
def convert_numpy(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def deep_convert(obj):
    if isinstance(obj, dict):
        return {k: deep_convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_convert(i) for i in obj]
    else:
        return convert_numpy(obj)


all_results = deep_convert(all_results)

with open(OUTPUT_FILE, "w") as f:
    json.dump(all_results, f, indent=2)
print(f"\nResults saved to: {OUTPUT_FILE}")
