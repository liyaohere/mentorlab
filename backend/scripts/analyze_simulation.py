import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np


def load_results(path: str) -> list[dict]:
    results = []
    with open(path) as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def count_words(text: str) -> int:
    if not text:
        return 0
    return len(text.split())


def check_format(text: str) -> dict:
    if not text:
        return {
            "has_cause": False,
            "has_prediction": False,
            "has_next_step": False,
            "compliant": False,
        }
    t = text.upper()
    has_cause = (
        "CAUSE" in t
        and "**CAUSE" in text.upper().replace("** ", "**").replace(" **", "**")
        or "**CAUSE:" in text
        or "**CAUSE" in text
    )
    has_prediction = "PREDICTION" in t
    has_next_step = "NEXT STEP" in t
    return {
        "has_cause": has_cause,
        "has_prediction": has_prediction,
        "has_next_step": has_next_step,
        "compliant": has_cause and has_prediction and has_next_step,
    }


def analyze_format_and_wordcount(results: list[dict]) -> None:
    print("\n" + "=" * 70)
    print("FORMAT COMPLIANCE & WORD COUNTS")
    print("=" * 70)
    by_condition = defaultdict(list)
    for r in results:
        cond = r.get("condition", "unknown")
        shown = r.get("result", {}).get("shown")
        if shown is None:
            continue
        if isinstance(shown, list):
            total_words = sum(count_words(s) for s in shown)
            compliant = all(check_format(s)["compliant"] for s in shown)
            by_condition[cond].append(
                {
                    "profile_id": r.get("profile_id"),
                    "word_count": total_words,
                    "per_diagnosis_words": [count_words(s) for s in shown],
                    "format_compliant": compliant,
                    "num_diagnoses": len(shown),
                }
            )
        else:
            wc = count_words(shown)
            fmt = check_format(shown)
            by_condition[cond].append(
                {
                    "profile_id": r.get("profile_id"),
                    "word_count": wc,
                    "format_compliant": fmt["compliant"],
                    "format_detail": fmt,
                }
            )
    for cond in ["single", "integrated", "competing"]:
        items = by_condition.get(cond, [])
        if not items:
            continue
        word_counts = [i["word_count"] for i in items]
        compliant = sum(1 for i in items if i["format_compliant"])
        in_range = sum(1 for wc in word_counts if 130 <= wc <= 200)
        print(f"\n--- {cond.upper()} (n={len(items)}) ---")
        print(
            f"  Format compliance: {compliant}/{len(items)} ({compliant / len(items) * 100:.0f}%)"
        )
        print(
            f"  Word count: mean={np.mean(word_counts):.0f}, "
            f"SD={np.std(word_counts):.0f}, "
            f"range=[{min(word_counts)}, {max(word_counts)}]"
        )
        print(
            f"  In 130-200 range: {in_range}/{len(items)} ({in_range / len(items) * 100:.0f}%)"
        )
        # Flag outliers
        for i in items:
            if not i["format_compliant"]:
                print(f"  [FORMAT FAIL] {i['profile_id']}")
            if i["word_count"] < 130 or i["word_count"] > 200:
                print(f"  [WORD COUNT] {i['profile_id']}: {i['word_count']} words")
        if cond == "competing":
            per_diag = [
                w
                for i in items
                if "per_diagnosis_words" in i
                for w in i["per_diagnosis_words"]
            ]
            if per_diag:
                print(
                    f"  Per-diagnosis words: mean={np.mean(per_diag):.0f}, "
                    f"SD={np.std(per_diag):.0f}, range=[{min(per_diag)}, {max(per_diag)}]"
                )


def analyze_divergence(results: list[dict]) -> None:
    """Check 3: Divergence check pass/fail rate."""
    print("\n" + "=" * 70)
    print("DIVERGENCE CHECK")
    print("=" * 70)
    for cond in ["integrated", "competing"]:
        checks = [
            r.get("result", {}).get("divergence_check", "")
            for r in results
            if r.get("condition") == cond
            and r.get("result", {}).get("divergence_check")
        ]
        if not checks:
            continue
        passes = sum(1 for c in checks if c.startswith("PASS"))
        fails = sum(1 for c in checks if c.startswith("FAIL"))
        print(f"\n--- {cond.upper()} (n={len(checks)}) ---")
        print(f"  PASS: {passes} ({passes / len(checks) * 100:.0f}%)")
        print(f"  FAIL: {fails} ({fails / len(checks) * 100:.0f}%)")
        for c in checks:
            if c.startswith("FAIL"):
                print(f"  [FAIL] {c[:100]}")


def analyze_responses(results: list[dict]) -> None:
    """Check 5: Response differentiation across conditions."""
    print("\n" + "=" * 70)
    print("SIMULATED RESPONSE ANALYSIS")
    print("=" * 70)
    multi_words = [
        "but",
        "however",
        "on the other hand",
        "alternatively",
        "another",
        "different",
        "multiple",
        "several",
        "various",
        "tension",
        "competing",
        "disagree",
    ]
    by_condition = defaultdict(list)
    for r in results:
        resp = r.get("simulated_response")
        if not resp:
            continue
        cond = r.get("condition", "unknown")
        wc = count_words(resp)
        multi_count = sum(1 for w in multi_words if w.lower() in resp.lower())
        by_condition[cond].append(
            {
                "profile_id": r.get("profile_id"),
                "word_count": wc,
                "multi_perspective_mentions": multi_count,
                "response_preview": resp[:150],
            }
        )
    for cond in ["single", "integrated", "competing"]:
        items = by_condition.get(cond, [])
        if not items:
            continue
        word_counts = [i["word_count"] for i in items]
        multi_counts = [i["multi_perspective_mentions"] for i in items]
        print(f"\n--- {cond.upper()} (n={len(items)}) ---")
        print(
            f"  Response words: mean={np.mean(word_counts):.0f}, SD={np.std(word_counts):.0f}"
        )
        print(
            f"  Multi-perspective mentions: mean={np.mean(multi_counts):.1f}, "
            f"SD={np.std(multi_counts):.1f}"
        )
    # Within-subject comparison (same profile across conditions)
    within_results = [r for r in results if r.get("test_type") == "within"]
    if within_results:
        print("\n--- WITHIN-SUBJECT: Same profile across conditions ---")
        by_profile = defaultdict(dict)
        for r in within_results:
            if r.get("simulated_response"):
                by_profile[r["profile_id"]][r["condition"]] = {
                    "multi": sum(
                        1
                        for w in multi_words
                        if w.lower() in r["simulated_response"].lower()
                    ),
                    "words": count_words(r["simulated_response"]),
                    "preview": r["simulated_response"][:100],
                }
        for pid, conds in sorted(by_profile.items())[:5]:
            print(f"\n  Profile {pid}:")
            for c in ["single", "integrated", "competing"]:
                if c in conds:
                    print(
                        f"    {c}: {conds[c]['words']}w, {conds[c]['multi']} multi-mentions | {conds[c]['preview']}..."
                    )


def analyze_survey(results: list[dict]) -> None:
    """Check 6: Survey pattern analysis."""
    print("\n" + "=" * 70)
    print("SIMULATED SURVEY ANALYSIS")
    print("=" * 70)
    survey_keys = [
        k
        for k, _ in [
            ("cognitive_load", ""),
            ("perceived_confusion", ""),
            ("trust_in_advice", ""),
            ("confidence", ""),
            ("ownership", ""),
            ("perceived_disagreement", ""),
            ("perceived_breadth", ""),
        ]
    ]
    by_condition: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in results:
        survey = r.get("simulated_survey")
        if not survey or "parse_error" in survey:
            continue
        cond = r.get("condition", "unknown")
        for key in survey_keys:
            val = survey.get(key)
            if val is not None and isinstance(val, (int, float)):
                by_condition[cond][key].append(float(val))
    header = f"{'Item':<30}"
    for cond in ["single", "integrated", "competing"]:
        header += f"  {cond:>15}"
    print(f"\n{header}")
    print("-" * len(header))
    for key in survey_keys:
        row = f"{key:<30}"
        for cond in ["single", "integrated", "competing"]:
            vals = by_condition.get(cond, {}).get(key, [])
            if vals:
                row += f"  {np.mean(vals):>6.1f} ({np.std(vals):.1f})"
            else:
                row += f"  {'N/A':>15}"
        print(row)
    # Check expected patterns
    print("\n--- EXPECTED PATTERN CHECKS ---")
    pd_single = by_condition.get("single", {}).get("perceived_disagreement", [])
    pd_integrated = by_condition.get("integrated", {}).get("perceived_disagreement", [])
    pd_competing = by_condition.get("competing", {}).get("perceived_disagreement", [])
    if pd_single and pd_competing:
        mean_s = np.mean(pd_single)
        mean_c = np.mean(pd_competing)
        print(
            f"  perceived_disagreement C3 > C1? {mean_c:.1f} vs {mean_s:.1f} -> {'YES' if mean_c > mean_s else 'NO'}"
        )
    pb_single = by_condition.get("single", {}).get("perceived_breadth", [])
    pb_competing = by_condition.get("competing", {}).get("perceived_breadth", [])
    if pb_single and pb_competing:
        mean_s = np.mean(pb_single)
        mean_c = np.mean(pb_competing)
        print(
            f"  perceived_breadth C3 >= C1? {mean_c:.1f} vs {mean_s:.1f} -> {'YES' if mean_c >= mean_s else 'NO'}"
        )
    trust_single = by_condition.get("single", {}).get("trust_in_advice", [])
    trust_integrated = by_condition.get("integrated", {}).get("trust_in_advice", [])
    if trust_single and trust_integrated:
        mean_s = np.mean(trust_single)
        mean_i = np.mean(trust_integrated)
        print(
            f"  trust_in_advice C2 >= C1? {mean_i:.1f} vs {mean_s:.1f} -> {'YES' if mean_i >= mean_s else 'NO'}"
        )


# ──────────────────────────────────────────────────────────────────────────
# NEW: between-subject equivalent of paper's Table C1 (manipulation checks)
# and Table E1 (process measures) — mean(SD) per condition + pairwise
# Mann-Whitney U across C3 vs C2, C2 vs C1, C3 vs C1.
#
# IMPORTANT CAVEAT (printed in the output too): the paper's Table C1 is a
# WITHIN-subject design (same 30 profiles run through all 3 conditions,
# N=90 paired observations). Our current data is BETWEEN-subject (each
# profile appears in exactly one condition), so this is a weaker,
# unpaired test -- same question ("are the 3 conditions balanced /
# do they differ as expected on these dimensions"), lower statistical
# power than a true paired design.
# ──────────────────────────────────────────────────────────────────────────
def rank_biserial(g_a: list[float], g_b: list[float], u_stat: float) -> float:
    """Rank-biserial correlation as effect size for Mann-Whitney U (g_a vs g_b).
    Ranges [-1, 1]; magnitude ~ |r| < .1 negligible, .1-.3 small, .3-.5 medium, >.5 large."""
    n1, n2 = len(g_a), len(g_b)
    if n1 == 0 or n2 == 0:
        return float("nan")
    return 1 - (2 * u_stat) / (n1 * n2)


def analyze_assignment_balance(results: list[dict]) -> None:
    """Check whether profiles assigned to the 3 conditions look systematically
    different on dimensions that should be unrelated to condition (profile_id
    order, industry mix). run_simulation.py assigns condition via `i % 3`
    on the position of each profile within its industry group -- NOT random
    sampling -- so if profile characteristics drift with generation order
    (plausible, since generate_profiles.py explicitly tells later batches to
    avoid repeating earlier profiles' challenges), that drift could leak into
    the condition comparison as a confound rather than being averaged away."""
    print("\n" + "=" * 70)
    print("ASSIGNMENT BALANCE CHECK (profile_id order & industry mix)")
    print("=" * 70)
    print(
        "Context: condition is assigned by position (i %% 3) within each\n"
        "industry group, not by random sampling. This checks whether the\n"
        "3 groups differ on dimensions that should be unrelated to condition.\n"
    )

    def pid_num(pid: str) -> int:
        digits = "".join(ch for ch in pid if ch.isdigit())
        return int(digits) if digits else -1

    by_condition_ids: dict[str, list[int]] = defaultdict(list)
    by_condition_industry: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for r in results:
        cond = r.get("condition")
        pid = r.get("profile_id")
        if not cond or not pid:
            continue
        by_condition_ids[cond].append(pid_num(pid))
        industry = r.get("industry_vertical") or (r.get("profile") or {}).get(
            "industry_vertical"
        )
        if industry:
            by_condition_industry[cond][industry] += 1

    print(f"{'Condition':<15}{'N':>6}{'mean profile_id#':>20}{'SD':>10}")
    for cond in ["single", "integrated", "competing"]:
        ids = by_condition_ids.get(cond, [])
        if not ids:
            continue
        print(f"{cond:<15}{len(ids):>6}{np.mean(ids):>20.1f}{np.std(ids):>10.1f}")

    try:
        from scipy.stats import kruskal

        groups = [v for v in by_condition_ids.values() if v]
        if len(groups) == 3 and all(len(g) > 1 for g in groups):
            h, p = kruskal(*groups)
            verdict = (
                "(significant -- groups differ in generation-order position!)"
                if p < 0.05
                else "(no evidence of order-based imbalance)"
            )
            print(
                f"\nKruskal-Wallis on profile_id# across conditions: H={h:.2f}, p={p:.3f} {verdict}"
            )
    except ImportError:
        pass

    if any(by_condition_industry.values()):
        print("\nIndustry mix by condition:")
        all_industries = sorted(
            {ind for d in by_condition_industry.values() for ind in d}
        )
        header = f"{'industry':<20}"
        for cond in ["single", "integrated", "competing"]:
            header += f"{cond:>15}"
        print(header)
        for ind in all_industries:
            row = f"{ind:<20}"
            for cond in ["single", "integrated", "competing"]:
                row += f"{by_condition_industry.get(cond, {}).get(ind, 0):>15}"
            print(row)
    else:
        print(
            "\n(industry_vertical not found on records -- if you want this check,\n"
            "make sure run_single() saves profile['industry_vertical'] onto the record,\n"
            "or pass the original profiles.json separately and join on profile_id.)"
        )


def rank_biserial(g_a: list[float], g_b: list[float], u_stat: float) -> float:
    """Rank-biserial correlation as effect size for Mann-Whitney U (g_a vs g_b).
    Ranges [-1, 1]; magnitude ~ |r| < .1 negligible, .1-.3 small, .3-.5 medium, >.5 large."""
    n1, n2 = len(g_a), len(g_b)
    if n1 == 0 or n2 == 0:
        return float("nan")
    # Fixed sign mismatch: inverted the formula
    return (2 * u_stat) / (n1 * n2) - 1


def analyze_survey_stats(results: list[dict]) -> None:
    try:
        from scipy.stats import mannwhitneyu
    except ImportError:
        print(
            "\n[SKIPPED] scipy not installed -- run: pip install scipy --break-system-packages"
        )
        return

    print("\n" + "=" * 90)
    print(
        "BETWEEN-SUBJECT MANIPULATION CHECKS & PROCESS MEASURES (Table C1 / E1 equivalent)"
    )
    print("=" * 90)

    manipulation_checks = ["perceived_disagreement", "perceived_breadth"]
    process_measures = [
        "cognitive_load",
        "perceived_confusion",
        "trust_in_advice",
        "confidence",
        "ownership",
    ]
    all_items = manipulation_checks + process_measures

    by_condition: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in results:
        survey = r.get("simulated_survey")
        if not survey or "parse_error" in survey:
            continue
        cond = r.get("condition", "unknown")
        for key in all_items:
            val = survey.get(key)
            if val is not None and isinstance(val, (int, float)):
                by_condition[cond][key].append(float(val))

    def fmt_p(p: float) -> str:
        if p < 0.001:
            return "<.001"
        return f"{p:.3f}"

    header = (
        f"{'Item':<24}{'single (C1)':>14}{'integrated (C2)':>18}{'competing (C3)':>16}"
        f"{'C3 vs C2':>12}{'C2 vs C1':>12}{'C3 vs C1':>12}"
    )
    print(header)
    print("-" * len(header))

    def effect_label(r: float) -> str:
        ar = abs(r)
        if ar != ar:  # nan
            return ""
        if ar < 0.1:
            return "negligible"
        if ar < 0.3:
            return "small"
        if ar < 0.5:
            return "medium"
        return "large"

    def print_section(title, items):
        print(f"\n{title}")
        for key in items:
            g1 = by_condition.get("single", {}).get(key, [])
            g2 = by_condition.get("integrated", {}).get(key, [])
            g3 = by_condition.get("competing", {}).get(key, [])
            if not (g1 and g2 and g3):
                print(f"  {key:<22} -- insufficient data")
                continue
            m1, s1 = np.mean(g1), np.std(g1)
            m2, s2 = np.mean(g2), np.std(g2)
            m3, s3 = np.mean(g3), np.std(g3)

            u_32, p_32 = mannwhitneyu(g3, g2, alternative="two-sided")
            u_21, p_21 = mannwhitneyu(g2, g1, alternative="two-sided")
            u_31, p_31 = mannwhitneyu(g3, g1, alternative="two-sided")

            # Apply Bonferroni correction for multiple comparisons
            # TODO: I am not quite familiar with statistical correction,
            # so maybe we should do a double check.
            comparisons = 3
            p_32_adj = min(p_32 * comparisons, 1.0)
            p_21_adj = min(p_21 * comparisons, 1.0)
            p_31_adj = min(p_31 * comparisons, 1.0)

            row = (
                f"  {key:<22}{m1:>7.2f} ({s1:.2f}){m2:>10.2f} ({s2:.2f})"
                f"{m3:>8.2f} ({s3:.2f}){fmt_p(p_32_adj):>12}{fmt_p(p_21_adj):>12}{fmt_p(p_31_adj):>12}"
            )
            print(row)
            r_32 = rank_biserial(g3, g2, u_32)
            r_21 = rank_biserial(g2, g1, u_21)
            r_31 = rank_biserial(g3, g1, u_31)
            print(
                f"  {'  mean diff / effect r':<22}"
                f"{'':>7}{'':>10}{'':>8}"
                f"{m3 - m2:>+7.2f} r={r_32:>+.2f} ({effect_label(r_32)})"
                f"  {m2 - m1:>+7.2f} r={r_21:>+.2f} ({effect_label(r_21)})"
                f"  {m3 - m1:>+7.2f} r={r_31:>+.2f} ({effect_label(r_31)})"
            )

    print_section("Manipulation checks", manipulation_checks)
    print_section("Process measures", process_measures)


def analyze_pipeline_stats(results: list[dict]) -> None:
    """Pipeline reliability: errors, latency, token usage."""
    print("\n" + "=" * 70)
    print("PIPELINE RELIABILITY")
    print("=" * 70)
    errors = [r for r in results if r.get("errors")]
    print(f"\nTotal runs: {len(results)}")
    print(f"Runs with errors: {len(errors)} ({len(errors) / len(results) * 100:.0f}%)")
    for e in errors:
        print(f"  [{e.get('profile_id')}] {e.get('condition')}: {e.get('errors')}")
    by_condition = defaultdict(list)
    for r in results:
        if r.get("wall_clock_seconds"):
            by_condition[r["condition"]].append(
                {
                    "latency": r["wall_clock_seconds"],
                    "input_tokens": r.get("total_input_tokens", 0),
                    "output_tokens": r.get("total_output_tokens", 0),
                }
            )
    print(
        f"\n{'Condition':<15} {'Latency (s)':<20} {'Input tokens':<20} {'Output tokens':<20}"
    )
    print("-" * 75)
    for cond in ["single", "integrated", "competing"]:
        items = by_condition.get(cond, [])
        if not items:
            continue
        lats = [i["latency"] for i in items]
        inp = [i["input_tokens"] for i in items]
        out = [i["output_tokens"] for i in items]
        print(
            f"{cond:<15} {np.mean(lats):>6.1f} +/- {np.std(lats):>5.1f}  "
            f"{np.mean(inp):>7.0f} +/- {np.std(inp):>5.0f}  "
            f"{np.mean(out):>7.0f} +/- {np.std(out):>5.0f}"
        )


def print_go_nogo(results: list[dict]) -> None:
    """Print go/no-go summary against success criteria."""
    print("\n" + "=" * 70)
    print("GO / NO-GO CHECKLIST")
    print("=" * 70)
    total = len(results)
    errors = sum(1 for r in results if r.get("errors"))
    div_checks = [r for r in results if r.get("result", {}).get("divergence_check")]
    div_pass = sum(
        1 for r in div_checks if r["result"]["divergence_check"].startswith("PASS")
    )
    format_ok = 0
    format_total = 0
    for r in results:
        shown = r.get("result", {}).get("shown")
        if shown is None:
            continue
        if isinstance(shown, list):
            format_total += 1
            if all(check_format(s)["compliant"] for s in shown):
                format_ok += 1
        else:
            format_total += 1
            if check_format(shown)["compliant"]:
                format_ok += 1
    wc_ok = 0
    wc_total = 0
    for r in results:
        shown = r.get("result", {}).get("shown")
        if shown is None:
            continue
        if isinstance(shown, list):
            wc_total += 1
            total_wc = sum(count_words(s) for s in shown)
            if 130 <= total_wc <= 600:
                wc_ok += 1
        else:
            wc_total += 1
            wc = count_words(shown)
            if 130 <= wc <= 200:
                wc_ok += 1
    checks = [
        (
            "Pipeline error rate < 5%",
            errors / total * 100 < 5 if total else False,
            f"{errors}/{total} = {errors / total * 100:.0f}%",
        ),
        (
            "Divergence pass rate > 80%",
            div_pass / len(div_checks) * 100 > 80 if div_checks else False,
            f"{div_pass}/{len(div_checks)} = {div_pass / len(div_checks) * 100:.0f}%"
            if div_checks
            else "N/A",
        ),
        (
            "Format compliance > 90%",
            format_ok / format_total * 100 > 90 if format_total else False,
            f"{format_ok}/{format_total} = {format_ok / format_total * 100:.0f}%"
            if format_total
            else "N/A",
        ),
        (
            "Word count in range > 90%",
            wc_ok / wc_total * 100 > 90 if wc_total else False,
            f"{wc_ok}/{wc_total} = {wc_ok / wc_total * 100:.0f}%"
            if wc_total
            else "N/A",
        ),
    ]
    for desc, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {desc} -- {detail}")


def print_sample_outputs(results: list[dict], n: int = 3) -> None:
    """Print sample outputs for manual review."""
    print("\n" + "=" * 70)
    print(f"SAMPLE OUTPUTS (first {n} per condition)")
    print("=" * 70)
    for cond in ["single", "integrated", "competing"]:
        cond_results = [
            r
            for r in results
            if r.get("condition") == cond and r.get("result", {}).get("shown")
        ]
        print(f"\n{'=' * 40} {cond.upper()} {'=' * 40}")
        for r in cond_results[:n]:
            shown = r["result"]["shown"]
            if isinstance(shown, list):
                text = "\n---\n".join(shown)
            else:
                text = shown
            print(f"\n--- {r['profile_id']} ---")
            print(text[:500])
            if r.get("simulated_response"):
                print(f"\n  [SIM RESPONSE]: {r['simulated_response'][:200]}...")
            if r.get("simulated_survey") and "parse_error" not in r.get(
                "simulated_survey", {}
            ):
                print(f"  [SIM SURVEY]: {json.dumps(r['simulated_survey'])}")
            print()


def main():
    parser = argparse.ArgumentParser(description="Analyze MentorLab simulation results")
    parser.add_argument("--input", required=True, help="Path to results .jsonl file")
    parser.add_argument(
        "--samples", type=int, default=3, help="Number of sample outputs per condition"
    )
    args = parser.parse_args()
    if not Path(args.input).exists():
        print(f"ERROR: File not found: {args.input}")
        sys.exit(1)
    results = load_results(args.input)
    print(f"Loaded {len(results)} results from {args.input}")
    # Filter to successful runs
    valid = [r for r in results if r.get("result")]
    print(f"Valid runs (with diagnosis result): {len(valid)}")
    analyze_pipeline_stats(results)
    analyze_divergence(valid)
    analyze_format_and_wordcount(valid)
    analyze_responses(results)
    analyze_survey(results)
    analyze_survey_stats(results)
    analyze_assignment_balance(results)
    print_go_nogo(results)
    # print_sample_outputs(valid, n=args.samples)


if __name__ == "__main__":
    main()
