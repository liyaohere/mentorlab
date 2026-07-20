"""
Heuristic DV coding for directional check.

Uses text-level features to approximate the 5 formulation quality dimensions.
Not a substitute for expert coding or LLM-as-coder, but captures key signals
that should differ across conditions if the manipulation works.
"""

import json
import re
from pathlib import Path
from statistics import mean, stdev
from collections import Counter

# ── Text feature extractors ──────────────────────────────────────────


def count_causes(text: str) -> int:
    """Count nonredundant causal claims. Looks for distinct cause-indicating segments."""
    # Split into sentences
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    cause_indicators = [
        r"\b(?:the (?:biggest|most important|main|pressing|key|core|real) (?:problem|issue|challenge))",
        r"\b(?:because|due to|caused by|stems from|result of|driven by)",
        r"\b(?:another (?:issue|problem|challenge|factor))",
        r"\b(?:also (?:need|important|crucial|affects?))",
        r"\b(?:additionally|furthermore|moreover|on top of)",
        r"\b(?:both .+ and)",
        r"\b(?:not only .+ but)",
    ]

    # Count sentences with causal content
    causal_sentences = set()
    for i, sent in enumerate(sentences):
        for pattern in cause_indicators:
            if re.search(pattern, sent, re.IGNORECASE):
                causal_sentences.add(i)
                break

    # Also count distinct problem topics using keyword clustering
    problem_words = re.findall(
        r"\b(cash flow|credit|supply|demand|competition|marketing|location|"
        r"price|cost|quality|transport|waste|power|internet|training|staff|"
        r"rain|weather|season|customer|inventory|supplier|delivery|fund|capital|"
        r"infrastructure|reputation|visibility|regulation|skill|technology|"
        r"shelf life|storage|spoilage|foot traffic|online|branding)\b",
        text.lower(),
    )
    distinct_topics = len(set(problem_words))

    # Comprehensiveness = max(causal sentences, distinct topics capped at 4)
    return max(len(causal_sentences), min(distinct_topics, 4), 1)


def causal_evaluation_score(text: str) -> float:
    """Score 1-5: does the response evaluate multiple causes?"""
    text_lower = text.lower()

    # Comparison/evaluation markers
    comparison_words = [
        "however",
        "but",
        "although",
        "while",
        "whereas",
        "on the other hand",
        "alternatively",
        "instead",
        "more important",
        "most pressing",
        "seems to be",
        "i think",
        "i believe",
        "i agree",
        "i realize",
        "weighing",
        "considering",
        "balancing",
    ]
    hedge_words = [
        "seems",
        "appears",
        "might",
        "could be",
        "likely",
        "probably",
        "perhaps",
        "may be",
    ]
    multi_cause = [
        "both",
        "combination",
        "multiple",
        "several",
        "not only",
        "as well as",
        "in addition",
        "alongside",
        "also need",
        "also important",
        "dual",
        "twofold",
    ]

    comparison_count = sum(1 for w in comparison_words if w in text_lower)
    hedge_count = sum(1 for w in hedge_words if w in text_lower)
    multi_count = sum(1 for w in multi_cause if w in text_lower)

    score = 1.0
    score += min(comparison_count * 0.5, 1.5)
    score += min(hedge_count * 0.3, 0.5)
    score += min(multi_count * 0.5, 1.5)
    score += min(count_causes(text) - 1, 1) * 0.5  # bonus for multiple causes

    return min(round(score, 1), 5.0)


def cause_clarity_score(text: str) -> float:
    """Score 1-5: does the response name a specific cause?"""
    text_lower = text.lower()

    # Cause-identification markers
    cause_markers = [
        "the (?:biggest|most important|main|core|key|real|pressing) (?:problem|issue|challenge)",
        "the (?:problem|issue|challenge) is",
        "because",
        "due to",
        "stems from",
        "caused by",
        "root cause",
        "underlying",
    ]
    specificity_markers = [
        # References to specific business elements
        r"\b(?:my|our|the) (?:stall|shop|farm|business|stand|store|center|studio)",
        r"\b(?:customers?|clients?|suppliers?|competitors?)\b",
        r"(?:cash flow|credit|inventory|delivery|supply chain)",
    ]

    cause_count = sum(1 for p in cause_markers if re.search(p, text_lower))
    spec_count = sum(1 for p in specificity_markers if re.search(p, text_lower))

    score = 1.0
    score += min(cause_count * 0.6, 2.0)
    score += min(spec_count * 0.4, 1.5)

    # Length bonus — longer responses tend to have more detail
    words = len(text.split())
    if words > 80:
        score += 0.5

    return min(round(score, 1), 5.0)


def assumption_score(text: str) -> float:
    """Score 1-5: does the response surface assumptions?"""
    text_lower = text.lower()

    assumption_markers = [
        "if ",
        "assuming",
        "this assumes",
        "provided that",
        "given that",
        "as long as",
        "depends on",
        "i think",
        "i believe",
        "it seems",
        "it appears",
        "might not",
        "may not",
        "could be wrong",
        "not sure",
        "uncertain",
    ]

    count = sum(1 for m in assumption_markers if m in text_lower)
    score = 1.0 + min(count * 0.6, 3.0)

    # Conditional language bonus
    if re.search(r"\bif\b.*\bthen\b", text_lower):
        score += 0.5

    return min(round(score, 1), 5.0)


def evidence_score(text: str) -> float:
    """Score 1-5: does the response propose discriminating evidence?"""
    text_lower = text.lower()

    evidence_markers = [
        "test",
        "try",
        "experiment",
        "measure",
        "track",
        "see if",
        "see whether",
        "check",
        "monitor",
        "find out",
        "assess",
        "evaluate",
        "compare",
        "survey",
        "ask customers",
        "feedback",
        "if this works",
        "if it doesn't",
    ]

    count = sum(1 for m in evidence_markers if m in text_lower)
    score = 1.0 + min(count * 0.8, 3.0)

    return min(round(score, 1), 5.0)


def coherence_score(text: str) -> float:
    """Score 1-5: does the action address the identified cause?"""
    text_lower = text.lower()

    # Action markers
    action_markers = [
        "my next step",
        "i plan to",
        "i will",
        "i need to",
        "should be to",
        "going to",
        "i'll",
        "i intend",
        "to tackle this",
        "to address this",
        "to solve",
        "my plan",
        "the solution",
    ]

    # Linking markers (cause → action)
    linking_markers = [
        "therefore",
        "so",
        "this means",
        "that's why",
        "to address this",
        "to tackle this",
        "in order to",
        "this will help",
        "this should",
        "which will",
        "by doing this",
        "by doing so",
    ]

    action_count = sum(1 for m in action_markers if m in text_lower)
    link_count = sum(1 for m in linking_markers if m in text_lower)

    score = 1.5  # baseline — most responses have some action
    score += min(action_count * 0.4, 1.5)
    score += min(link_count * 0.5, 1.5)

    return min(round(score, 1), 5.0)


def novelty_score(text: str) -> float:
    """Score 1-5: does the formulation go beyond obvious causes?"""
    text_lower = text.lower()

    # Generic/obvious phrases (lower novelty)
    generic = [
        "more customers",
        "increase sales",
        "reduce costs",
        "improve quality",
        "better marketing",
        "save money",
        "grow my business",
        "attract more",
    ]
    # Deeper/non-obvious phrases (higher novelty)
    novel = [
        "combination of",
        "underlying",
        "root cause",
        "not just",
        "beyond",
        "reframe",
        "rethink",
        "the real issue",
        "actually",
        "counterintuitive",
        "perception",
        "reputation",
        "positioning",
        "diversif",
        "long-term",
        "structural",
    ]

    generic_count = sum(1 for g in generic if g in text_lower)
    novel_count = sum(1 for n in novel if n in text_lower)

    score = 2.0  # baseline
    score -= min(generic_count * 0.3, 1.0)
    score += min(novel_count * 0.5, 2.0)

    return max(min(round(score, 1), 5.0), 1.0)


# ── Main ─────────────────────────────────────────────────────────────


def main():
    runs_dir = Path(__file__).parent / "simulation_results" / "runs"
    jsonl_file = runs_dir / "run008_20260720_opus_across.jsonl"

    across_runs = []
    with open(jsonl_file) as f:
        for line in f:
            rec = json.loads(line)
            if rec["test_type"] == "across" and rec.get("simulated_response"):
                across_runs.append(rec)

    print(f"Coding {len(across_runs)} across-subject responses (heuristic)...")

    dims = [
        "cause_clarity",
        "causal_evaluation",
        "assumption_identification",
        "discriminating_evidence",
        "cause_action_coherence",
        "comprehensiveness",
        "novelty",
    ]

    results = []
    for run in across_runs:
        text = run["simulated_response"]
        r = {
            "run_id": run["run_id"],
            "condition": run["condition"],
            "profile_id": run["profile_id"],
            "cause_clarity": cause_clarity_score(text),
            "causal_evaluation": causal_evaluation_score(text),
            "assumption_identification": assumption_score(text),
            "discriminating_evidence": evidence_score(text),
            "cause_action_coherence": coherence_score(text),
            "comprehensiveness": count_causes(text),
            "novelty": novelty_score(text),
            "word_count": len(text.split()),
        }
        results.append(r)

    # Save
    out_path = Path(__file__).parent / "simulation_results" / "dv_coding_heuristic.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    # ── Analysis ──
    print("\n" + "=" * 75)
    print("PROBLEM FORMULATION QUALITY BY CONDITION (heuristic-coded)")
    print("=" * 75)

    for cond in ["single", "integrated", "competing"]:
        cr = [r for r in results if r["condition"] == cond]
        print(f"\n--- {cond.upper()} (N={len(cr)}) ---")
        for dim in dims:
            vals = [r[dim] for r in cr]
            m = mean(vals)
            s = stdev(vals) if len(vals) > 1 else 0
            print(f"  {dim:30s}: M={m:.2f}  SD={s:.2f}")

    # ── Composite ──
    print("\n" + "=" * 75)
    print("COMPOSITE (mean of 5 primary dimensions, excl. comprehensiveness & novelty)")
    print("=" * 75)
    for cond in ["single", "integrated", "competing"]:
        cr = [r for r in results if r["condition"] == cond]
        composites = [mean([r[d] for d in dims[:5]]) for r in cr]
        m = mean(composites)
        s = stdev(composites) if len(composites) > 1 else 0
        print(f"  {cond:15s}: M={m:.2f}  SD={s:.2f}")

    # ── Statistical tests ──
    print("\n" + "=" * 75)
    print("KRUSKAL-WALLIS + PAIRWISE TESTS")
    print("=" * 75)
    from scipy.stats import kruskal, mannwhitneyu

    for dim in dims + ["composite"]:
        groups = []
        for cond in ["single", "integrated", "competing"]:
            cr = [r for r in results if r["condition"] == cond]
            if dim == "composite":
                vals = [mean([r[d] for d in dims[:5]]) for r in cr]
            else:
                vals = [r[dim] for r in cr]
            groups.append(vals)

        H, p = kruskal(*groups)
        m1, m2, m3 = mean(groups[0]), mean(groups[1]), mean(groups[2])
        sig = (
            "***"
            if p < 0.001
            else "**"
            if p < 0.01
            else "*"
            if p < 0.05
            else "†"
            if p < 0.10
            else "ns"
        )

        print(
            f"  {dim:30s}: C1={m1:.2f}  C2={m2:.2f}  C3={m3:.2f}  H={H:.2f}  p={p:.4f} {sig}"
        )

        if p < 0.10:
            # H1: C3 > C2
            U, p32 = mannwhitneyu(groups[2], groups[1], alternative="greater")
            # H2: C2 > C1
            U, p21 = mannwhitneyu(groups[1], groups[0], alternative="greater")
            # C3 > C1
            U, p31 = mannwhitneyu(groups[2], groups[0], alternative="greater")
            print(
                f"    H1 (C3>C2): p={p32:.4f}  |  H2 (C2>C1): p={p21:.4f}  |  C3>C1: p={p31:.4f}"
            )

    # ── Key hypothesis tests summary ──
    print("\n" + "=" * 75)
    print("HYPOTHESIS-LEVEL SUMMARY")
    print("=" * 75)

    # H1: C3 (competing/separate) > C2 (integrated) on formulation quality
    c2_comp = [
        mean([r[d] for d in dims[:5]])
        for r in results
        if r["condition"] == "integrated"
    ]
    c3_comp = [
        mean([r[d] for d in dims[:5]]) for r in results if r["condition"] == "competing"
    ]
    c1_comp = [
        mean([r[d] for d in dims[:5]]) for r in results if r["condition"] == "single"
    ]

    U, p_h1 = mannwhitneyu(c3_comp, c2_comp, alternative="greater")
    print(
        f"  H1 (preserved > resolved): C3 M={mean(c3_comp):.2f} vs C2 M={mean(c2_comp):.2f}"
    )
    print(f"    Mann-Whitney U={U:.0f}, p={p_h1:.4f} (one-sided)")

    U, p_h2 = mannwhitneyu(c2_comp, c1_comp, alternative="greater")
    print(
        f"  H2 (multi-integrated > single): C2 M={mean(c2_comp):.2f} vs C1 M={mean(c1_comp):.2f}"
    )
    print(f"    Mann-Whitney U={U:.0f}, p={p_h2:.4f} (one-sided)")

    # ── Dimension most likely to differ: causal evaluation & comprehensiveness ──
    print("\n" + "=" * 75)
    print("KEY DIMENSIONS (most theoretically relevant)")
    print("=" * 75)
    for dim in ["causal_evaluation", "comprehensiveness"]:
        g1 = [r[dim] for r in results if r["condition"] == "single"]
        g2 = [r[dim] for r in results if r["condition"] == "integrated"]
        g3 = [r[dim] for r in results if r["condition"] == "competing"]
        H, p = kruskal(g1, g2, g3)
        print(f"\n  {dim}:")
        print(
            f"    C1={mean(g1):.2f}  C2={mean(g2):.2f}  C3={mean(g3):.2f}  (H={H:.2f}, p={p:.4f})"
        )
        U, p32 = mannwhitneyu(g3, g2, alternative="greater")
        U, p21 = mannwhitneyu(g2, g1, alternative="greater")
        print(f"    H1 (C3>C2): p={p32:.4f}  |  H2 (C2>C1): p={p21:.4f}")


if __name__ == "__main__":
    main()
