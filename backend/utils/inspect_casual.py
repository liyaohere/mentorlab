import argparse
import json
import re
import sys
from pathlib import Path

COMPARISON_WORDS = [
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

HEDGE_WORDS = [
    "seems",
    "appears",
    "might",
    "could be",
    "likely",
    "probably",
    "perhaps",
    "may be",
]

MULTI_CAUSE = [
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

PROBLEM_WORDS_PATTERN = (
    r"\b(cash flow|credit|supply|demand|competition|marketing|location|"
    r"price|cost|quality|transport|waste|power|internet|training|staff|"
    r"rain|weather|season|customer|inventory|supplier|delivery|fund|capital|"
    r"infrastructure|reputation|visibility|regulation|skill|technology|"
    r"shelf life|storage|spoilage|foot traffic|online|branding)\b"
)

CAUSE_INDICATORS = [
    r"\b(?:the (?:biggest|most important|main|pressing|key|core|real) (?:problem|issue|challenge))",
    r"\b(?:because|due to|caused by|stems from|result of|driven by)",
    r"\b(?:another (?:issue|problem|challenge|factor))",
    r"\b(?:also (?:need|important|crucial|affects?))",
    r"\b(?:additionally|furthermore|moreover|on top of)",
    r"\b(?:both .+ and)",
    r"\b(?:not only .+ but)",
]


def count_causes(text: str) -> int:
    """Count potential cause indicators and distinct problem topics in the text."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    causal_sentences = set()
    for i, sent in enumerate(sentences):
        for pattern in CAUSE_INDICATORS:
            if re.search(pattern, sent, re.IGNORECASE):
                causal_sentences.add(i)
                break

    problem_words = re.findall(PROBLEM_WORDS_PATTERN, text.lower())
    distinct_topics = len(set(problem_words))

    return max(len(causal_sentences), min(distinct_topics, 4), 1)


def causal_evaluation_score(text: str) -> tuple[float, dict]:
    """Calculate causal evaluation score and return score details."""
    text_lower = text.lower()
    hit_comparison = [w for w in COMPARISON_WORDS if w in text_lower]
    hit_hedge = [w for w in HEDGE_WORDS if w in text_lower]
    hit_multi = [w for w in MULTI_CAUSE if w in text_lower]

    score = 1.0
    score += min(len(hit_comparison) * 0.5, 1.5)
    score += min(len(hit_hedge) * 0.3, 0.5)
    score += min(len(hit_multi) * 0.5, 1.5)

    causes = count_causes(text)
    score += min(causes - 1, 1) * 0.5
    score = min(round(score, 1), 5.0)

    detail = {
        "hit_comparison_words": hit_comparison,
        "hit_hedge_words": hit_hedge,
        "hit_multi_cause_words": hit_multi,
        "count_causes": causes,
    }
    return score, detail


def load_jsonl(path: Path) -> list[dict]:
    """Load JSONL records from a specified path."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def main():
    parser = argparse.ArgumentParser(
        description="Extract top and bottom scoring simulated_response samples for manual inspection."
    )
    parser.add_argument("--input", required=True, help="Input JSONL file path")
    parser.add_argument(
        "--condition",
        default=None,
        help="Filter by specific condition (single/integrated/competing)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=4,
        help="Number of top and bottom samples to display per condition (default: 4)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    records = load_jsonl(input_path)
    across = [
        r
        for r in records
        if r.get("test_type") == "across" and r.get("simulated_response")
    ]
    print(f"Loaded {len(across)} across-subject records\n")

    conditions = (
        [args.condition] if args.condition else ["single", "integrated", "competing"]
    )

    scored = []
    for r in across:
        text = r["simulated_response"]
        score, detail = causal_evaluation_score(text)
        scored.append(
            {
                "profile_id": r.get("profile_id"),
                "condition": r.get("condition"),
                "score": score,
                "detail": detail,
                "text": text,
            }
        )

    for cond in conditions:
        cr = [s for s in scored if s["condition"] == cond]
        if not cr:
            continue

        cr_sorted = sorted(cr, key=lambda x: x["score"])
        lowest = cr_sorted[: args.top_n]
        highest = cr_sorted[-args.top_n :][::-1]

        print("=" * 80)
        print(f"{cond.upper()} (N={len(cr)})  -- Lowest {args.top_n} scores")
        print("=" * 80)
        for s in lowest:
            print(f"\n--- {s['profile_id']}  score={s['score']} ---")
            print(f"  Hit comparison words: {s['detail']['hit_comparison_words']}")
            print(f"  Hit hedge words: {s['detail']['hit_hedge_words']}")
            print(f"  Hit multi-cause words: {s['detail']['hit_multi_cause_words']}")
            print(f"  count_causes: {s['detail']['count_causes']}")
            print(f"  Text: {s['text']}")

        print("\n" + "=" * 80)
        print(f"{cond.upper()} (N={len(cr)})  -- Highest {args.top_n} scores")
        print("=" * 80)
        for s in highest:
            print(f"\n--- {s['profile_id']}  score={s['score']} ---")
            print(f"  Hit comparison words: {s['detail']['hit_comparison_words']}")
            print(f"  Hit hedge words: {s['detail']['hit_hedge_words']}")
            print(f"  Hit multi-cause words: {s['detail']['hit_multi_cause_words']}")
            print(f"  count_causes: {s['detail']['count_causes']}")
            print(f"  Text: {s['text']}")
        print()


if __name__ == "__main__":
    main()
