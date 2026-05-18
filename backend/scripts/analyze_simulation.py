"""
Analyze simulation results from MentorLab V2 agent-based tests.

Produces a comprehensive report: format compliance, word counts, divergence stats,
simulated response differentiation, and survey pattern analysis.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/analyze_simulation.py --input scripts/simulation_results/results_sonnet_both.jsonl
"""

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
    """Check if text contains CAUSE/PREDICTION/NEXT STEP structure."""
    if not text:
        return {"has_cause": False, "has_prediction": False, "has_next_step": False, "compliant": False}
    t = text.upper()
    has_cause = "CAUSE" in t and "**CAUSE" in text.upper().replace("** ", "**").replace(" **", "**") or "**CAUSE:" in text or "**CAUSE" in text
    has_prediction = "PREDICTION" in t
    has_next_step = "NEXT STEP" in t
    return {
        "has_cause": has_cause,
        "has_prediction": has_prediction,
        "has_next_step": has_next_step,
        "compliant": has_cause and has_prediction and has_next_step,
    }


def analyze_format_and_wordcount(results: list[dict]) -> None:
    """Check 1-2: Format compliance and word counts."""
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
            # C3: check each of 3 diagnoses
            total_words = sum(count_words(s) for s in shown)
            compliant = all(check_format(s)["compliant"] for s in shown)
            by_condition[cond].append({
                "profile_id": r.get("profile_id"),
                "word_count": total_words,
                "per_diagnosis_words": [count_words(s) for s in shown],
                "format_compliant": compliant,
                "num_diagnoses": len(shown),
            })
        else:
            wc = count_words(shown)
            fmt = check_format(shown)
            by_condition[cond].append({
                "profile_id": r.get("profile_id"),
                "word_count": wc,
                "format_compliant": fmt["compliant"],
                "format_detail": fmt,
            })

    for cond in ["single", "integrated", "competing"]:
        items = by_condition.get(cond, [])
        if not items:
            continue

        word_counts = [i["word_count"] for i in items]
        compliant = sum(1 for i in items if i["format_compliant"])
        in_range = sum(1 for wc in word_counts if 130 <= wc <= 200)

        print(f"\n--- {cond.upper()} (n={len(items)}) ---")
        print(f"  Format compliance: {compliant}/{len(items)} ({compliant/len(items)*100:.0f}%)")
        print(f"  Word count: mean={np.mean(word_counts):.0f}, "
              f"SD={np.std(word_counts):.0f}, "
              f"range=[{min(word_counts)}, {max(word_counts)}]")
        print(f"  In 130-200 range: {in_range}/{len(items)} ({in_range/len(items)*100:.0f}%)")

        # Flag outliers
        for i in items:
            if not i["format_compliant"]:
                print(f"  [FORMAT FAIL] {i['profile_id']}")
            if i["word_count"] < 130 or i["word_count"] > 200:
                print(f"  [WORD COUNT] {i['profile_id']}: {i['word_count']} words")

        # C3: also show per-diagnosis stats
        if cond == "competing":
            per_diag = [w for i in items if "per_diagnosis_words" in i for w in i["per_diagnosis_words"]]
            if per_diag:
                print(f"  Per-diagnosis words: mean={np.mean(per_diag):.0f}, "
                      f"SD={np.std(per_diag):.0f}, range=[{min(per_diag)}, {max(per_diag)}]")


def analyze_divergence(results: list[dict]) -> None:
    """Check 3: Divergence check pass/fail rate."""
    print("\n" + "=" * 70)
    print("DIVERGENCE CHECK")
    print("=" * 70)

    for cond in ["integrated", "competing"]:
        checks = [
            r.get("result", {}).get("divergence_check", "")
            for r in results
            if r.get("condition") == cond and r.get("result", {}).get("divergence_check")
        ]
        if not checks:
            continue

        passes = sum(1 for c in checks if c.startswith("PASS"))
        fails = sum(1 for c in checks if c.startswith("FAIL"))
        print(f"\n--- {cond.upper()} (n={len(checks)}) ---")
        print(f"  PASS: {passes} ({passes/len(checks)*100:.0f}%)")
        print(f"  FAIL: {fails} ({fails/len(checks)*100:.0f}%)")
        for c in checks:
            if c.startswith("FAIL"):
                print(f"  [FAIL] {c[:100]}")


def analyze_responses(results: list[dict]) -> None:
    """Check 5: Response differentiation across conditions."""
    print("\n" + "=" * 70)
    print("SIMULATED RESPONSE ANALYSIS")
    print("=" * 70)

    # Hedging/multi-perspective words
    multi_words = ["but", "however", "on the other hand", "alternatively",
                   "another", "different", "multiple", "several", "various",
                   "tension", "competing", "disagree"]

    by_condition = defaultdict(list)
    for r in results:
        resp = r.get("simulated_response")
        if not resp:
            continue
        cond = r.get("condition", "unknown")

        wc = count_words(resp)
        multi_count = sum(1 for w in multi_words if w.lower() in resp.lower())

        by_condition[cond].append({
            "profile_id": r.get("profile_id"),
            "word_count": wc,
            "multi_perspective_mentions": multi_count,
            "response_preview": resp[:150],
        })

    for cond in ["single", "integrated", "competing"]:
        items = by_condition.get(cond, [])
        if not items:
            continue

        word_counts = [i["word_count"] for i in items]
        multi_counts = [i["multi_perspective_mentions"] for i in items]

        print(f"\n--- {cond.upper()} (n={len(items)}) ---")
        print(f"  Response words: mean={np.mean(word_counts):.0f}, SD={np.std(word_counts):.0f}")
        print(f"  Multi-perspective mentions: mean={np.mean(multi_counts):.1f}, "
              f"SD={np.std(multi_counts):.1f}")

    # Within-subject comparison (same profile across conditions)
    within_results = [r for r in results if r.get("test_type") == "within"]
    if within_results:
        print("\n--- WITHIN-SUBJECT: Same profile across conditions ---")
        by_profile = defaultdict(dict)
        for r in within_results:
            if r.get("simulated_response"):
                by_profile[r["profile_id"]][r["condition"]] = {
                    "multi": sum(1 for w in multi_words if w.lower() in r["simulated_response"].lower()),
                    "words": count_words(r["simulated_response"]),
                    "preview": r["simulated_response"][:100],
                }

        for pid, conds in sorted(by_profile.items())[:5]:
            print(f"\n  Profile {pid}:")
            for c in ["single", "integrated", "competing"]:
                if c in conds:
                    print(f"    {c}: {conds[c]['words']}w, {conds[c]['multi']} multi-mentions | {conds[c]['preview']}...")


def analyze_survey(results: list[dict]) -> None:
    """Check 6: Survey pattern analysis."""
    print("\n" + "=" * 70)
    print("SIMULATED SURVEY ANALYSIS")
    print("=" * 70)

    survey_keys = [k for k, _ in [
        ("cognitive_load", ""), ("perceived_confusion", ""),
        ("trust_in_advice", ""), ("confidence", ""), ("ownership", ""),
        ("perceived_disagreement", ""), ("perceived_breadth", ""),
    ]]

    by_condition: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for r in results:
        survey = r.get("simulated_survey")
        if not survey or "parse_error" in survey:
            continue
        cond = r.get("condition", "unknown")
        for key in survey_keys:
            val = survey.get(key)
            if val is not None and isinstance(val, (int, float)):
                by_condition[cond][key].append(float(val))

    # Print table
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
        print(f"  perceived_disagreement C3 > C1? {mean_c:.1f} vs {mean_s:.1f} -> {'YES' if mean_c > mean_s else 'NO'}")

    pb_single = by_condition.get("single", {}).get("perceived_breadth", [])
    pb_competing = by_condition.get("competing", {}).get("perceived_breadth", [])
    if pb_single and pb_competing:
        mean_s = np.mean(pb_single)
        mean_c = np.mean(pb_competing)
        print(f"  perceived_breadth C3 >= C1? {mean_c:.1f} vs {mean_s:.1f} -> {'YES' if mean_c >= mean_s else 'NO'}")

    trust_single = by_condition.get("single", {}).get("trust_in_advice", [])
    trust_integrated = by_condition.get("integrated", {}).get("trust_in_advice", [])
    if trust_single and trust_integrated:
        mean_s = np.mean(trust_single)
        mean_i = np.mean(trust_integrated)
        print(f"  trust_in_advice C2 >= C1? {mean_i:.1f} vs {mean_s:.1f} -> {'YES' if mean_i >= mean_s else 'NO'}")


def analyze_pipeline_stats(results: list[dict]) -> None:
    """Pipeline reliability: errors, latency, token usage."""
    print("\n" + "=" * 70)
    print("PIPELINE RELIABILITY")
    print("=" * 70)

    errors = [r for r in results if r.get("errors")]
    print(f"\nTotal runs: {len(results)}")
    print(f"Runs with errors: {len(errors)} ({len(errors)/len(results)*100:.0f}%)")
    for e in errors:
        print(f"  [{e.get('profile_id')}] {e.get('condition')}: {e.get('errors')}")

    by_condition = defaultdict(list)
    for r in results:
        if r.get("wall_clock_seconds"):
            by_condition[r["condition"]].append({
                "latency": r["wall_clock_seconds"],
                "input_tokens": r.get("total_input_tokens", 0),
                "output_tokens": r.get("total_output_tokens", 0),
            })

    print(f"\n{'Condition':<15} {'Latency (s)':<20} {'Input tokens':<20} {'Output tokens':<20}")
    print("-" * 75)
    for cond in ["single", "integrated", "competing"]:
        items = by_condition.get(cond, [])
        if not items:
            continue
        lats = [i["latency"] for i in items]
        inp = [i["input_tokens"] for i in items]
        out = [i["output_tokens"] for i in items]
        print(f"{cond:<15} {np.mean(lats):>6.1f} +/- {np.std(lats):>5.1f}  "
              f"{np.mean(inp):>7.0f} +/- {np.std(inp):>5.0f}  "
              f"{np.mean(out):>7.0f} +/- {np.std(out):>5.0f}")


def print_go_nogo(results: list[dict]) -> None:
    """Print go/no-go summary against success criteria."""
    print("\n" + "=" * 70)
    print("GO / NO-GO CHECKLIST")
    print("=" * 70)

    total = len(results)
    errors = sum(1 for r in results if r.get("errors"))

    # Divergence
    div_checks = [r for r in results if r.get("result", {}).get("divergence_check")]
    div_pass = sum(1 for r in div_checks if r["result"]["divergence_check"].startswith("PASS"))

    # Format
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

    # Word count
    wc_ok = 0
    wc_total = 0
    for r in results:
        shown = r.get("result", {}).get("shown")
        if shown is None:
            continue
        if isinstance(shown, list):
            wc_total += 1
            total_wc = sum(count_words(s) for s in shown)
            if 130 <= total_wc <= 600:  # C3: 3 x ~60-70 words each = 180-210 total
                wc_ok += 1
        else:
            wc_total += 1
            wc = count_words(shown)
            if 130 <= wc <= 200:
                wc_ok += 1

    checks = [
        ("Pipeline error rate < 5%", errors / total * 100 < 5 if total else False,
         f"{errors}/{total} = {errors/total*100:.0f}%"),
        ("Divergence pass rate > 80%", div_pass / len(div_checks) * 100 > 80 if div_checks else False,
         f"{div_pass}/{len(div_checks)} = {div_pass/len(div_checks)*100:.0f}%" if div_checks else "N/A"),
        ("Format compliance > 90%", format_ok / format_total * 100 > 90 if format_total else False,
         f"{format_ok}/{format_total} = {format_ok/format_total*100:.0f}%" if format_total else "N/A"),
        ("Word count in range > 90%", wc_ok / wc_total * 100 > 90 if wc_total else False,
         f"{wc_ok}/{wc_total} = {wc_ok/wc_total*100:.0f}%" if wc_total else "N/A"),
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
        cond_results = [r for r in results if r.get("condition") == cond and r.get("result", {}).get("shown")]
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
            if r.get("simulated_survey") and "parse_error" not in r.get("simulated_survey", {}):
                print(f"  [SIM SURVEY]: {json.dumps(r['simulated_survey'])}")
            print()


def main():
    parser = argparse.ArgumentParser(description="Analyze MentorLab simulation results")
    parser.add_argument("--input", required=True, help="Path to results .jsonl file")
    parser.add_argument("--samples", type=int, default=3, help="Number of sample outputs per condition")
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
    print_go_nogo(results)
    print_sample_outputs(valid, n=args.samples)


if __name__ == "__main__":
    main()
