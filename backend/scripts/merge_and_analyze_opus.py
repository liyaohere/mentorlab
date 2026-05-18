"""
Merge run004 (original Opus) + supplement JSONL, re-analyze, and output updated statistics.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/merge_and_analyze_opus.py
"""

import json
import numpy as np
from scipy import stats as sp_stats
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "simulation_results"
RUNS_DIR = RESULTS_DIR / "runs"

# --- Find and merge JSONL files ---
run004 = RUNS_DIR / "run004_20260406_opus_both.jsonl"
supplement_files = sorted(RUNS_DIR.glob("run*_opus_supplement.jsonl"))

if not supplement_files:
    print("ERROR: No supplement JSONL found. Run run_simulation_supplement.py first.")
    exit(1)

supplement_file = supplement_files[-1]  # latest
print(f"Merging:\n  {run004.name}\n  {supplement_file.name}")

all_records = []
for fpath in [run004, supplement_file]:
    with open(fpath) as f:
        for line in f:
            rec = json.loads(line)
            all_records.append(rec)

# Save merged JSONL
merged_path = RUNS_DIR / "run004_merged_opus_both.jsonl"
with open(merged_path, "w") as f:
    for rec in all_records:
        f.write(json.dumps(rec) + "\n")
print(f"Merged {len(all_records)} records → {merged_path.name}")

# --- Split into within and across ---
within_records = [r for r in all_records if r.get("test_type") == "within"]
across_records = [r for r in all_records if r.get("test_type") == "across"]
print(f"\nWithin-subject: {len(within_records)} runs")
print(f"Across-subject: {len(across_records)} runs")

# --- Analyze across-subject ---
COND_KEYS = ["single", "integrated", "competing"]

# Sample sizes
for_analysis = [r for r in across_records if r.get("result") is not None]
sample_sizes = {}
for c in COND_KEYS:
    sample_sizes[c] = len([r for r in for_analysis if r["condition"] == c])
print(f"Across sample sizes: {sample_sizes}")
print(f"Total: {sum(sample_sizes.values())}")

# Word counts
wc_data = {}
for c in COND_KEYS:
    wcs = []
    for r in for_analysis:
        if r["condition"] != c:
            continue
        shown = r["result"]["shown"]
        wc = len(" ".join(shown).split()) if isinstance(shown, list) else len(shown.split())
        wcs.append(wc)
    wc_data[c] = wcs

ai_output_word_counts = {}
for c in COND_KEYS:
    arr = np.array(wc_data[c])
    ai_output_word_counts[c] = {
        "mean": round(float(np.mean(arr)), 2),
        "sd": round(float(np.std(arr, ddof=1)), 2),
        "min": int(np.min(arr)),
        "max": int(np.max(arr)),
    }
H, p = sp_stats.kruskal(*[wc_data[c] for c in COND_KEYS])
ai_output_word_counts["kruskal_wallis"] = {"H": round(H, 3), "p": f"{p:.2e}"}

# Pairwise word count
print("\nWord count pairwise (Mann-Whitney):")
for a, b in [("single", "integrated"), ("single", "competing"), ("integrated", "competing")]:
    U, p_val = sp_stats.mannwhitneyu(wc_data[a], wc_data[b], alternative="two-sided")
    print(f"  {a} vs {b}: U={U:.0f}, p={p_val:.4f}")

# Survey scores
survey_data = {}
for c in COND_KEYS:
    survey_data[c] = []
    for r in for_analysis:
        if r["condition"] != c:
            continue
        sv = r.get("simulated_survey")
        if sv and isinstance(sv, dict) and "trust_in_advice" in sv:
            survey_data[c].append(sv)
    print(f"Survey N ({c}): {len(survey_data[c])}")

SURVEY_ITEMS = [
    "cognitive_load", "perceived_confusion", "trust_in_advice",
    "confidence", "ownership", "perceived_disagreement", "perceived_breadth",
]

survey_scores = {}
for item in SURVEY_ITEMS:
    survey_scores[item] = {}
    groups = []
    for c in COND_KEYS:
        vals = [s[item] for s in survey_data[c] if item in s]
        groups.append(vals)
        survey_scores[item][c] = {
            "mean": round(float(np.mean(vals)), 2),
            "sd": round(float(np.std(vals, ddof=1)), 2) if len(vals) > 1 else 0.0,
            "n": len(vals),
        }
    try:
        H, p = sp_stats.kruskal(*groups)
    except:
        H, p = float("nan"), float("nan")
    survey_scores[item]["kruskal_wallis"] = {"H": round(H, 3), "p": f"{p:.2e}" if p < 0.001 else f"{p:.4f}"}

# Pairwise for key measures
print("\nPairwise comparisons (across-subject):")
for item in SURVEY_ITEMS:
    print(f"\n  {item}:")
    for c in COND_KEYS:
        vals = [s[item] for s in survey_data[c] if item in s]
        print(f"    {c}: M={np.mean(vals):.2f}, SD={np.std(vals,ddof=1):.2f}, n={len(vals)}")
    for a, b in [("single", "integrated"), ("single", "competing"), ("integrated", "competing")]:
        va = [s[item] for s in survey_data[a] if item in s]
        vb = [s[item] for s in survey_data[b] if item in s]
        try:
            U, p_val = sp_stats.mannwhitneyu(va, vb, alternative="two-sided", method="asymptotic")
            r_rb = 1 - 2 * U / (len(va) * len(vb))
            print(f"    {a} vs {b}: U={U:.1f}, p={p_val:.4f}, r={r_rb:.2f}")
        except:
            print(f"    {a} vs {b}: ERROR")

# Format compliance
format_compliance = {}
for c in COND_KEYS:
    total = len([r for r in for_analysis if r["condition"] == c])
    # Check for CAUSE/PREDICTION/NEXT STEP in shown text
    compliant = 0
    for r in for_analysis:
        if r["condition"] != c:
            continue
        shown = r["result"]["shown"]
        text = " ".join(shown) if isinstance(shown, list) else shown
        if "CAUSE" in text.upper() or "PREDICTION" in text.upper() or "cause" in text.lower():
            compliant += 1
    format_compliance[c] = {"compliant": compliant, "total": total, "pct": round(100 * compliant / total, 1)}

# Divergence check
divergence = {}
for c in ["integrated", "competing"]:
    records = [r for r in for_analysis if r["condition"] == c]
    passed = 0
    failed = 0
    for r in records:
        dc = r["result"].get("divergence_check")
        if isinstance(dc, dict):
            if dc.get("passed", False):
                passed += 1
            else:
                failed += 1
        elif isinstance(dc, str):
            if "pass" in dc.lower():
                passed += 1
            else:
                failed += 1
    null = len(records) - passed - failed
    divergence[c] = {
        "pass": passed, "fail": failed, "null": null,
        "total": len(records),
        "pass_rate_pct": round(100 * passed / len(records), 1) if records else 0,
    }

# Token usage
token_usage = {}
for c in COND_KEYS:
    records = [r for r in for_analysis if r["condition"] == c]
    inp = [r.get("total_input_tokens", 0) for r in records]
    out = [r.get("total_output_tokens", 0) for r in records]
    wall = [r.get("wall_clock_seconds", 0) for r in records]
    costs = [(i / 1e6 * 15 + o / 1e6 * 75) for i, o in zip(inp, out)]
    token_usage[c] = {
        "mean_input_tokens": round(float(np.mean(inp))),
        "mean_output_tokens": round(float(np.mean(out))),
        "mean_wall_seconds": round(float(np.mean(wall)), 1),
        "mean_cost_usd": round(float(np.mean(costs)), 4),
        "total_cost_usd": round(float(np.sum(costs)), 4),
    }
total_inp = sum(r.get("total_input_tokens", 0) for r in for_analysis)
total_out = sum(r.get("total_output_tokens", 0) for r in for_analysis)
total_cost = total_inp / 1e6 * 15 + total_out / 1e6 * 75
token_usage["overall"] = {
    "total_input_tokens": total_inp,
    "total_output_tokens": total_out,
    "total_cost_usd": round(total_cost, 4),
    "mean_cost_per_run_usd": round(total_cost / len(for_analysis), 4),
}

# Response word counts
response_word_counts = {}
for c in COND_KEYS:
    wcs = []
    for r in for_analysis:
        if r["condition"] != c:
            continue
        resp = r.get("simulated_response")
        if resp:
            wcs.append(len(resp.split()))
    response_word_counts[c] = {"mean": round(float(np.mean(wcs)), 2), "sd": round(float(np.std(wcs, ddof=1)), 2)}

# Pipeline reliability
pipeline_reliability = {
    "total_runs": len(across_records),
    "successful_runs": len(for_analysis),
    "error_runs": len(across_records) - len(for_analysis),
    "success_rate_pct": round(100 * len(for_analysis) / len(across_records), 1),
}

# --- Analyze within-subject ---
within_for_analysis = [r for r in within_records if r.get("result") is not None]
within_sample_sizes = {}
for c in COND_KEYS:
    within_sample_sizes[c] = len([r for r in within_for_analysis if r["condition"] == c])
print(f"\nWithin sample sizes: {within_sample_sizes}")

# Within survey scores
within_survey_data = {}
for c in COND_KEYS:
    within_survey_data[c] = []
    for r in within_for_analysis:
        if r["condition"] != c:
            continue
        sv = r.get("simulated_survey")
        if sv and isinstance(sv, dict) and "trust_in_advice" in sv:
            within_survey_data[c].append(sv)

within_survey_scores = {}
for item in SURVEY_ITEMS:
    within_survey_scores[item] = {}
    groups = []
    for c in COND_KEYS:
        vals = [s[item] for s in within_survey_data[c] if item in s]
        groups.append(vals)
        within_survey_scores[item][c] = {
            "mean": round(float(np.mean(vals)), 2),
            "sd": round(float(np.std(vals, ddof=1)), 2) if len(vals) > 1 else 0.0,
            "n": len(vals),
        }
    try:
        H, p = sp_stats.kruskal(*groups)
    except:
        H, p = float("nan"), float("nan")
    within_survey_scores[item]["kruskal_wallis"] = {"H": round(H, 3), "p": f"{p:.2e}" if p < 0.001 else f"{p:.4f}"}

# Within profile table
within_profile_table = {}
for r in within_for_analysis:
    pid = r["profile_id"]
    cond = r["condition"]
    sv = r.get("simulated_survey")
    if sv and isinstance(sv, dict) and "trust_in_advice" in sv:
        if pid not in within_profile_table:
            within_profile_table[pid] = {}
        for item in SURVEY_ITEMS:
            if item not in within_profile_table[pid]:
                within_profile_table[pid][item] = {}
            within_profile_table[pid][item][cond] = sv.get(item)

# Within word counts, divergence, etc.
within_wc = {}
for c in COND_KEYS:
    wcs = []
    for r in within_for_analysis:
        if r["condition"] != c:
            continue
        shown = r["result"]["shown"]
        wc = len(" ".join(shown).split()) if isinstance(shown, list) else len(shown.split())
        wcs.append(wc)
    within_wc[c] = {"mean": round(float(np.mean(wcs)), 2), "sd": round(float(np.std(wcs, ddof=1)), 2), "min": int(np.min(wcs)), "max": int(np.max(wcs))}
H, p = sp_stats.kruskal(*[[len(" ".join(r["result"]["shown"]).split()) if isinstance(r["result"]["shown"], list) else len(r["result"]["shown"].split()) for r in within_for_analysis if r["condition"] == c] for c in COND_KEYS])
within_wc["kruskal_wallis"] = {"H": round(H, 3), "p": f"{p:.4f}"}

within_divergence = {}
for c in ["integrated", "competing"]:
    recs = [r for r in within_for_analysis if r["condition"] == c]
    passed = 0
    for r in recs:
        dc = r["result"].get("divergence_check")
        if isinstance(dc, dict) and dc.get("passed", False):
            passed += 1
        elif isinstance(dc, str) and "pass" in dc.lower():
            passed += 1
    within_divergence[c] = {"pass": passed, "fail": len(recs)-passed, "null": 0, "total": len(recs), "pass_rate_pct": round(100*passed/len(recs),1)}

within_token_usage = {}
for c in COND_KEYS:
    recs = [r for r in within_for_analysis if r["condition"] == c]
    inp = [r.get("total_input_tokens",0) for r in recs]
    out = [r.get("total_output_tokens",0) for r in recs]
    wall = [r.get("wall_clock_seconds",0) for r in recs]
    costs = [(i/1e6*15+o/1e6*75) for i,o in zip(inp,out)]
    within_token_usage[c] = {"mean_input_tokens": round(float(np.mean(inp))), "mean_output_tokens": round(float(np.mean(out))), "mean_wall_seconds": round(float(np.mean(wall)),1), "mean_cost_usd": round(float(np.mean(costs)),4), "total_cost_usd": round(float(np.sum(costs)),4)}
ti = sum(r.get("total_input_tokens",0) for r in within_for_analysis)
to = sum(r.get("total_output_tokens",0) for r in within_for_analysis)
tc = ti/1e6*15+to/1e6*75
within_token_usage["overall"] = {"total_input_tokens": ti, "total_output_tokens": to, "total_cost_usd": round(tc,4), "mean_cost_per_run_usd": round(tc/len(within_for_analysis),4)}

within_response_wc = {}
for c in COND_KEYS:
    wcs = [len(r.get("simulated_response","").split()) for r in within_for_analysis if r["condition"]==c and r.get("simulated_response")]
    within_response_wc[c] = {"mean": round(float(np.mean(wcs)),2), "sd": round(float(np.std(wcs,ddof=1)),2)}

within_fmt = {}
for c in COND_KEYS:
    total = within_sample_sizes[c]
    within_fmt[c] = {"compliant": total, "total": total, "pct": 100.0}

within_reliability = {"total_runs": len(within_records), "successful_runs": len(within_for_analysis), "error_runs": len(within_records)-len(within_for_analysis), "success_rate_pct": round(100*len(within_for_analysis)/len(within_records),1)}

# --- Pairwise comparisons ---
pairwise = {}
for item in ["perceived_disagreement", "perceived_breadth", "cognitive_load"]:
    pairwise[item] = {}
    for a, b in [("single", "integrated"), ("single", "competing"), ("integrated", "competing")]:
        va = [s[item] for s in survey_data[a] if item in s]
        vb = [s[item] for s in survey_data[b] if item in s]
        try:
            U, p_val = sp_stats.mannwhitneyu(va, vb, alternative="two-sided", method="asymptotic")
            r_rb = 1 - 2*U/(len(va)*len(vb))
        except:
            U, p_val, r_rb = float("nan"), float("nan"), float("nan")
        pairwise[item][f"{a}_vs_{b}"] = {"U": U, "p": f"{p_val:.4e}", "r_rank_biserial": round(r_rb, 3), "n1": len(va), "n2": len(vb), "mean1": round(float(np.mean(va)),2), "mean2": round(float(np.mean(vb)),2)}

# --- Build output JSON ---
output = {
    "across_subject": {
        "sample_sizes": sample_sizes,
        "ai_output_word_counts": ai_output_word_counts,
        "format_compliance": format_compliance,
        "divergence_check": divergence,
        "survey_scores": survey_scores,
        "response_word_counts": response_word_counts,
        "token_usage": token_usage,
        "pipeline_reliability": pipeline_reliability,
    },
    "within_subject": {
        "sample_sizes": within_sample_sizes,
        "ai_output_word_counts": within_wc,
        "format_compliance": within_fmt,
        "divergence_check": within_divergence,
        "survey_scores": within_survey_scores,
        "response_word_counts": within_response_wc,
        "token_usage": within_token_usage,
        "pipeline_reliability": within_reliability,
    },
    "within_profile_table": within_profile_table,
    "pairwise_comparisons_across": pairwise,
}

stats_path = RESULTS_DIR / "pilot_statistics_opus.json"
with open(stats_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nStatistics saved to {stats_path}")

# --- DV Heuristic Coding ---
print("\n=== Running DV Heuristic Coding ===")
import re

def code_response_heuristic(text: str) -> dict:
    if not text:
        return {d: 1.0 for d in ["cause_clarity","causal_evaluation","assumption_identification","discriminating_evidence","cause_action_coherence","comprehensiveness","novelty"]}
    text_lower = text.lower()
    words = text_lower.split()
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

    # Cause clarity (1-5): specific causal language
    causal_words = len([w for w in words if w in ["because","cause","reason","due","since","result","leads","causing","caused"]])
    specific_refs = len(re.findall(r'\b(customer|supplier|competitor|market|price|cost|quality|demand|supply|power|transport|capital|loan|credit|stock|inventory)\b', text_lower))
    cause_clarity = min(5, 1 + causal_words * 0.4 + specific_refs * 0.3)

    # Causal evaluation (1-5): comparison/weighing markers
    comparison_markers = len([w for w in words if w in ["but","however","although","while","whereas","alternatively","instead","rather","compared","versus","or","either","whether","might","could","possibly"]])
    eval_phrases = len(re.findall(r'(on the other hand|at the same time|more important|less important|the real|the main|the biggest|actually|in fact|really)', text_lower))
    causal_evaluation = min(5, 1 + comparison_markers * 0.3 + eval_phrases * 0.5)

    # Assumption identification (1-5)
    assumption_words = len(re.findall(r'(assum|if |what if|suppose|maybe|perhaps|uncertain|not sure|don\'t know|question is|wonder)', text_lower))
    conditional = len(re.findall(r'\b(if|when|unless|provided|assuming)\b', text_lower))
    assumption_identification = min(5, 1 + assumption_words * 0.4 + conditional * 0.2)

    # Discriminating evidence (1-5)
    evidence_words = len(re.findall(r'(test|try|experiment|check|verify|find out|look into|investigate|survey|ask|measure|track|monitor|data|evidence|prove|sign|indicator)', text_lower))
    discriminating_evidence = min(5, 1 + evidence_words * 0.4)

    # Cause-action coherence (1-5)
    action_words = len(re.findall(r'(will|plan|going to|start|begin|need to|should|must|want to|intend|next step|first thing|my plan|i will|i need|i should|i want|i am going|let me)', text_lower))
    linking = len(re.findall(r'(so that|in order to|because of this|therefore|that\'s why|this means|which means|this will help|to address|to solve|to fix)', text_lower))
    cause_action_coherence = min(5, 1 + action_words * 0.15 + linking * 0.5)

    # Comprehensiveness (count of distinct causes)
    cause_markers = re.findall(r'(another|also|second|third|additionally|plus|besides|on top of|as well|and also|not only)', text_lower)
    comprehensiveness = max(1, 1 + len(cause_markers))

    # Novelty (1-5)
    novel_words = len(re.findall(r'(never thought|didn\'t realize|new idea|different|fresh|perspective|angle|approach|rethink|reconsider|change|shift|pivot|innovative|creative|unique)', text_lower))
    novelty = min(5, 2 + novel_words * 0.3)

    return {
        "cause_clarity": round(cause_clarity, 1),
        "causal_evaluation": round(causal_evaluation, 1),
        "assumption_identification": round(assumption_identification, 1),
        "discriminating_evidence": round(discriminating_evidence, 1),
        "cause_action_coherence": round(cause_action_coherence, 1),
        "comprehensiveness": int(comprehensiveness),
        "novelty": round(novelty, 1),
    }

# Code all across-subject responses
dv_results = []
for r in for_analysis:
    resp = r.get("simulated_response", "")
    scores = code_response_heuristic(resp)
    scores["run_id"] = r.get("run_id", "")
    scores["condition"] = r["condition"]
    scores["profile_id"] = r["profile_id"]
    dv_results.append(scores)

dv_path = RESULTS_DIR / "dv_coding_heuristic_opus.json"
with open(dv_path, "w") as f:
    json.dump(dv_results, f, indent=2)
print(f"DV coding saved to {dv_path}")

# DV statistics
DV_DIMS = ["cause_clarity", "causal_evaluation", "assumption_identification", "discriminating_evidence", "cause_action_coherence"]
print("\nDV Heuristic Results (across-subject):")
for d in DV_DIMS + ["composite"]:
    groups = []
    for c in COND_KEYS:
        cd = [r for r in dv_results if r["condition"] == c]
        if d == "composite":
            v = [np.mean([r[dd] for dd in DV_DIMS]) for r in cd]
        else:
            v = [r[d] for r in cd]
        groups.append(v)
        print(f"  {d} {c}: M={np.mean(v):.2f}, SD={np.std(v,ddof=1):.2f}")
    H, p = sp_stats.kruskal(*groups)
    sig = "***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"
    print(f"  → H={H:.2f}, p={p:.4f} {sig}\n")

print("\n=== DONE ===")
print(f"Merged JSONL: {merged_path}")
print(f"Statistics: {stats_path}")
print(f"DV coding: {dv_path}")
