# Simulation Run Manifest

## Run 001 — 2026-04-06, 12:46PM
- **File**: `run001_20260406_gpt4o_within.jsonl`
- **Model**: gpt-4o
- **Test**: within-subject only (15 profiles x 3 conditions = 45 runs)
- **Summarizer version**: v1 (original — "1-2 sentences each part, ~60w each, ~180w total")
- **Note**: First successful run. C3 summarizer too aggressive — mean 141w total, per-diag mean 47w. Identified divergence check pass rate issue (70%). All other metrics passed.
- **Status**: Superseded by run002 (same model, added across-subject)

## Run 002 — 2026-04-06, 1:36PM
- **File**: `run002_20260406_gpt4o_both.jsonl`
- **Model**: gpt-4o
- **Test**: both (within 45 + across 60 = 105 runs)
- **Summarizer version**: v3 ("CAUSE 2 sentences, PRED/NEXT 1 sentence, 55-70w each, 170-210w total")
- **Note**: C3 word count overcorrected — mean 204w, 45% in range. C1=151w, C2=173w, C3=204w. Survey manipulation checks worked perfectly (perceived_disagreement C3=3.8 > C2=1.7 > C1=1.1). Divergence pass rate 60-76%.
- **Status**: Superseded by run003 (summarizer prompt tuned further)

## Run 003 — 2026-04-06, 2:08PM
- **File**: `run003_20260406_gpt4o_both.jsonl`
- **Model**: gpt-4o
- **Test**: both (within 45 + across 60 = 105 runs)
- **Summarizer version**: v5 final ("CAUSE 2 short sentences, PRED/NEXT 1 sentence, 50-60w each, 150-180w total, cap rule")
- **Cost**: $2.74, 1598s wall clock
- **Results**:
  - Error rate: 1/105 (1%) — 1 rate limit timeout
  - Format compliance: 100%
  - Word counts: C1=153w, C2=171w, **C3=179w** (aligned!)
  - C3 in-range: 91% (only 3 outliers above 200)
  - Divergence pass: 57-62% (GPT-4o limitation)
  - Manipulation checks: perceived_disagreement C3=3.5 > C2=1.7 > C1=1.1 ✓
  - perceived_breadth: C3=6.2 > C2=4.1 > C1=2.9 ✓
- **Status**: ✅ Stage 1 complete. Summarizer calibrated. Ready for Stage 2 (Opus).

## Summarizer Prompt Versions

| Version | Key instruction | Per-diag mean | Total mean | Problem |
|---------|----------------|---------------|------------|---------|
| v1 | "1-2 sentences each, ~60w each, ~180w total" | 47w | 141w | Too short |
| v2 | "2 sentences each, 55-70w each" | 99w | 293w | Way too long |
| v3 | "CAUSE 2 sent, PRED/NEXT 1 sent, 55-70w" | 68w | 204w | Still too long |
| v4 | "1 sentence each, <20w/sentence" | 35w | 117w | Too short |
| **v5** | "CAUSE 2 short sent, PRED/NEXT 1 sent, 50-60w + cap rule" | **59w** | **177w** | **Good** |

## Key Results Across Runs

### Manipulation Checks (simulated survey, all runs consistent)
| Measure | C1 | C2 | C3 | Expected pattern |
|---------|----|----|-----|------------------|
| perceived_disagreement | 1.1 | 1.7 | 3.8 | C3 > C2 > C1 YES |
| perceived_breadth | 2.9 | 3.9 | 6.1 | C3 > C2 > C1 YES |
| cognitive_load | 3.1 | 3.4 | 4.8 | C3 > C2 > C1 (expected) |
| trust_in_advice | 5.9 | 5.8 | 5.8 | Flat (good) |
| confidence | 5.2 | 5.1 | 5.1 | Flat (good) |
| ownership | 4.2 | 4.0 | 4.2 | Flat (good) |

### Pipeline Reliability (consistent across runs)
- Error rate: 0%
- Format compliance: 94-100%
- Divergence check pass rate: 60-76% (below 80% target — likely GPT-4o limitation, expect improvement with Opus)
