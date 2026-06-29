"""
AI-as-coder: Code problem formulation quality from simulated entrepreneur responses.

Codes 5 primary dimensions + 2 complementary measures, blinded to condition.
Uses GPT-4o as the coder (same model that generated the data — acknowledged limitation).

Dimensions (from paper Section 3.3):
  1. Cause clarity: specific underlying cause vs. restating symptoms
  2. Causal evaluation: evaluates plausibility of alternatives vs. adopts first one
  3. Assumption identification: surfaces assumptions in chosen cause
  4. Discriminating evidence: proposes test to distinguish among causes
  5. Cause-action coherence: revised plan addresses the identified cause
  + Comprehensiveness: count of nonredundant causes mentioned
  + Novelty: departure from obvious/surface-level causes
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv(Path(__file__).parent.parent / ".env")

CODING_PROMPT = """You are an expert coder for a research study on entrepreneurial problem formulation.
You will read an entrepreneur's description of their business challenge, and then their response
after receiving AI-generated advice. Your job is to rate the QUALITY of their problem formulation
in the response.

IMPORTANT: You are blinded to what type of advice they received. Focus only on what the
entrepreneur wrote in their response.

## Entrepreneur's Business Context
{intake_context}

## Entrepreneur's Response (to be coded)
"{response}"

## Coding Rubric

Rate each dimension on a 1-5 scale:

### 1. Cause Clarity (1-5)
Does the entrepreneur identify a specific underlying CAUSE of their problem, or merely restate symptoms?
- 1: Only restates the symptom (e.g., "sales are low") with no cause identification
- 2: Vaguely gestures at a cause but stays at symptom level
- 3: Identifies a plausible cause but in generic terms
- 4: Identifies a specific cause grounded in their business context
- 5: Identifies a precise, well-articulated cause with clear causal logic

### 2. Causal Evaluation (1-5)
Does the entrepreneur evaluate the relative plausibility of multiple possible causes, or simply adopt the first plausible one?
- 1: Adopts a single cause with no consideration of alternatives
- 2: Mentions one cause and acts on it without evaluation
- 3: Acknowledges alternatives exist but doesn't evaluate them
- 4: Considers multiple causes and explains why one is more plausible
- 5: Systematically weighs evidence for/against multiple causes before choosing

### 3. Assumption Identification (1-5)
Does the entrepreneur surface the assumptions embedded in their chosen cause?
- 1: No assumptions surfaced; takes the cause as self-evident
- 2: Implicitly assumes things but doesn't acknowledge them
- 3: Hints at an assumption (e.g., "if this is true...")
- 4: Explicitly states an assumption underlying their chosen cause
- 5: Identifies multiple assumptions and considers their validity

### 4. Discriminating Evidence (1-5)
Does the entrepreneur propose evidence or a test that would distinguish among alternative causes?
- 1: No mention of evidence or testing
- 2: Vague reference to "trying something" without a clear test
- 3: Proposes an action but not one that would distinguish causes
- 4: Proposes a specific test or evidence that would help distinguish causes
- 5: Designs a clear discriminating test with expected outcomes under different causes

### 5. Cause-Action Coherence (1-5)
Does the proposed next step logically address the identified cause, or does it sidestep it?
- 1: Action is unrelated to the stated cause
- 2: Action vaguely connects but doesn't directly address the cause
- 3: Action is reasonable but could address any cause
- 4: Action clearly targets the identified cause
- 5: Action is precisely calibrated to the cause, with clear causal logic connecting them

### 6. Comprehensiveness (count)
How many nonredundant, relevant causes does the entrepreneur mention? Count distinct causes.
(This is a count, not a 1-5 rating. Enter 1, 2, 3, etc.)

### 7. Novelty (1-5)
Does the formulation go beyond obvious or surface-level causes?
- 1: Completely surface-level, restates what anyone would say
- 2: Mostly obvious, with slight elaboration
- 3: Some depth beyond the obvious
- 4: Identifies a non-obvious cause or framing
- 5: Highly original insight that reframes the problem

## Output

Return ONLY valid JSON with these keys:
{{
  "cause_clarity": <1-5>,
  "causal_evaluation": <1-5>,
  "assumption_identification": <1-5>,
  "discriminating_evidence": <1-5>,
  "cause_action_coherence": <1-5>,
  "comprehensiveness": <count>,
  "novelty": <1-5>,
  "brief_rationale": "<1-2 sentences explaining your overall assessment>"
}}"""


async def code_response(client, profile: dict, response: str, run_id: str) -> dict:
    """Code a single response using GPT-4o."""
    # Build intake context (blinded — no condition info)
    intake = profile.get("intake_responses", {})
    context_parts = []
    if intake.get("business_description"):
        context_parts.append(f"Business: {intake['business_description']}")
    if intake.get("main_challenge"):
        context_parts.append(f"Challenge: {intake['main_challenge']}")
    if intake.get("current_plan"):
        context_parts.append(f"Current plan: {intake['current_plan']}")
    intake_context = "\n".join(context_parts)

    prompt = CODING_PROMPT.format(intake_context=intake_context, response=response)

    for attempt in range(3):
        try:
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.0,  # Deterministic for consistency
            )
            text = resp.choices[0].message.content.strip()
            # Parse JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            result = json.loads(text)
            result["run_id"] = run_id
            return result
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2**attempt)
            else:
                print(f"  ERROR coding {run_id}: {e}")
                return {"run_id": run_id, "error": str(e)}


async def main():
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # Load profiles
    profiles_path = Path(__file__).parent / "simulation_results" / "profiles.json"
    with open(profiles_path) as f:
        profiles_list = json.load(f)
    profiles = {p["id"]: p for p in profiles_list}

    # Load across-subject runs
    runs_dir = Path(__file__).parent / "simulation_results" / "runs"
    jsonl_file = runs_dir / "run003_20260406_gpt4o_both.jsonl"

    across_runs = []
    with open(jsonl_file) as f:
        for line in f:
            rec = json.loads(line)
            if (
                rec["test_type"] == "across"
                and "result" in rec
                and rec.get("simulated_response")
            ):
                across_runs.append(rec)

    print(f"Coding {len(across_runs)} across-subject responses...")
    print(
        f"Conditions: { {c: sum(1 for r in across_runs if r['condition'] == c) for c in ['single', 'integrated', 'competing']} }"
    )

    # Code all responses with concurrency limit
    sem = asyncio.Semaphore(3)
    results = []

    async def code_one(run):
        async with sem:
            profile = profiles.get(run["profile_id"], {})
            result = await code_response(
                client, profile, run["simulated_response"], run["run_id"]
            )
            result["condition"] = run["condition"]
            result["profile_id"] = run["profile_id"]
            results.append(result)
            done = len(results)
            if done % 10 == 0:
                print(f"  {done}/{len(across_runs)} coded...")

    tasks = [code_one(run) for run in across_runs]
    await asyncio.gather(*tasks)

    print(f"\nAll {len(results)} responses coded.")

    # Save raw results
    out_path = Path(__file__).parent / "simulation_results" / "dv_coding_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Raw results saved to {out_path}")

    # Analyze by condition
    dims = [
        "cause_clarity",
        "causal_evaluation",
        "assumption_identification",
        "discriminating_evidence",
        "cause_action_coherence",
        "comprehensiveness",
        "novelty",
    ]

    print("\n" + "=" * 70)
    print("PROBLEM FORMULATION QUALITY BY CONDITION (AI-coded, directional only)")
    print("=" * 70)

    from statistics import mean, stdev

    cond_data = {}
    for cond in ["single", "integrated", "competing"]:
        cond_results = [
            r for r in results if r["condition"] == cond and "error" not in r
        ]
        cond_data[cond] = cond_results
        print(f"\n--- Condition: {cond} (N={len(cond_results)}) ---")
        for dim in dims:
            vals = [r[dim] for r in cond_results if dim in r]
            if vals:
                m = mean(vals)
                s = stdev(vals) if len(vals) > 1 else 0
                print(
                    f"  {dim:30s}: M={m:.2f}  SD={s:.2f}  range=[{min(vals)}, {max(vals)}]"
                )

    # Composite score (mean of 5 primary dimensions)
    print("\n" + "=" * 70)
    print("COMPOSITE SCORE (mean of 5 primary dimensions)")
    print("=" * 70)
    for cond in ["single", "integrated", "competing"]:
        cond_results = [
            r for r in results if r["condition"] == cond and "error" not in r
        ]
        composites = []
        for r in cond_results:
            primary = [r.get(d) for d in dims[:5] if r.get(d) is not None]
            if len(primary) == 5:
                composites.append(mean(primary))
        if composites:
            m = mean(composites)
            s = stdev(composites) if len(composites) > 1 else 0
            print(f"  {cond:15s}: M={m:.2f}  SD={s:.2f}")

    # Kruskal-Wallis for each dimension
    print("\n" + "=" * 70)
    print("KRUSKAL-WALLIS TESTS")
    print("=" * 70)
    from scipy.stats import kruskal, mannwhitneyu

    for dim in dims + ["composite"]:
        groups = []
        for cond in ["single", "integrated", "competing"]:
            cond_results = [
                r for r in results if r["condition"] == cond and "error" not in r
            ]
            if dim == "composite":
                vals = []
                for r in cond_results:
                    primary = [r.get(d) for d in dims[:5] if r.get(d) is not None]
                    if len(primary) == 5:
                        vals.append(mean(primary))
            else:
                vals = [r[dim] for r in cond_results if dim in r]
            groups.append(vals)

        if all(len(g) > 0 for g in groups):
            H, p = kruskal(*groups)
            m1, m2, m3 = mean(groups[0]), mean(groups[1]), mean(groups[2])
            print(
                f"  {dim:30s}: C1={m1:.2f}  C2={m2:.2f}  C3={m3:.2f}  H={H:.2f}  p={p:.4f}"
            )

            # Pairwise: C3 vs C2 (H1), C2 vs C1 (H2)
            if p < 0.10:
                U_32, p_32 = mannwhitneyu(groups[2], groups[1], alternative="greater")
                U_21, p_21 = mannwhitneyu(groups[1], groups[0], alternative="greater")
                U_31, p_31 = mannwhitneyu(groups[2], groups[0], alternative="greater")
                print(
                    f"    Pairwise (one-sided): C3>C2 p={p_32:.4f}  C2>C1 p={p_21:.4f}  C3>C1 p={p_31:.4f}"
                )

    # Print a few example rationales
    print("\n" + "=" * 70)
    print("SAMPLE RATIONALES (1 per condition)")
    print("=" * 70)
    for cond in ["single", "integrated", "competing"]:
        for r in results:
            if r["condition"] == cond and "brief_rationale" in r:
                print(f"\n  [{cond.upper()}] {r['profile_id']}:")
                print(f"  {r['brief_rationale']}")
                break


if __name__ == "__main__":
    asyncio.run(main())
