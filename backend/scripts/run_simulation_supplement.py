"""
Incremental simulation: run 45 new profiles (P076-P120) through Opus pipeline.

- Within-subject: P076-P090 (15 profiles x 3 conditions = 45 runs)
- Across-subject: P091-P120 (30 profiles, forced 10/10/10 allocation to top up to 30/30/30)
- Total: 75 new Opus runs

Results are saved to a new JSONL file and can be merged with run004.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/run_simulation_supplement.py --concurrency 2
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Reuse everything from the main simulation script
from scripts.run_simulation import (
    TokenTracker, run_single, PROFILES_PATH, RESULTS_DIR, MODEL_MAP
)


async def main():
    parser = argparse.ArgumentParser(description="MentorLab V2 Supplemental Simulation")
    parser.add_argument("--concurrency", type=int, default=2, help="Max concurrent API calls")
    parser.add_argument("--test", choices=["within", "across", "both"], default="both")
    args = parser.parse_args()

    model = MODEL_MAP["opus"]
    print(f"=== MentorLab V2 Supplemental Simulation ===")
    print(f"Model: {model}")
    print(f"Concurrency: {args.concurrency}")

    # Load all profiles (should be 120 now)
    with open(PROFILES_PATH) as f:
        profiles = json.load(f)
    print(f"Loaded {len(profiles)} profiles")

    if len(profiles) < 120:
        print(f"ERROR: Expected 120 profiles, got {len(profiles)}. Run generate_profiles_supplement.py first.")
        sys.exit(1)

    tracker = TokenTracker(model=model, max_tokens=300)
    semaphore = asyncio.Semaphore(args.concurrency)
    all_results = []
    overall_start = time.time()

    # --- Within-subject: P076-P090 (indices 75-89) x 3 conditions ---
    if args.test in ("within", "both"):
        within_profiles = profiles[75:90]  # P076-P090
        conditions = ["single", "integrated", "competing"]
        tasks = []
        for profile in within_profiles:
            for cond in conditions:
                run_id = f"within_{profile['id']}_{cond}"
                tasks.append(run_single(profile, cond, tracker, semaphore, run_id, "within"))

        print(f"\n--- Within-Subject Supplement: {len(within_profiles)} profiles x 3 = {len(tasks)} runs ---")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                all_results.append({"error": str(r), "test_type": "within"})
                print(f"  ERROR: {r}")
            else:
                all_results.append(r)
        errors = sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, dict) and r.get("errors")))
        print(f"Completed: {len(results)} runs, {errors} with errors")

    # --- Across-subject: P091-P120 (indices 90-119), forced allocation ---
    if args.test in ("across", "both"):
        across_profiles = profiles[90:120]  # P091-P120

        # Force exact allocation: 10 single + 10 integrated + 12 competing
        # (to top up existing 22/20/18 → 30/30/30)
        # Wait: we need 8 + 10 + 12 = 30 to reach 30/30/30
        # Existing: single=22, integrated=20, competing=18
        # Need: single+8=30, integrated+10=30, competing+12=30
        allocation = (
            [("single", p) for p in across_profiles[:8]] +
            [("integrated", p) for p in across_profiles[8:18]] +
            [("competing", p) for p in across_profiles[18:30]]
        )

        tasks = []
        cond_counts = {}
        for cond, profile in allocation:
            cond_counts[cond] = cond_counts.get(cond, 0) + 1
            run_id = f"across_{profile['id']}_{cond}"
            tasks.append(run_single(profile, cond, tracker, semaphore, run_id, "across"))

        print(f"\n--- Across-Subject Supplement: {cond_counts} = {len(tasks)} runs ---")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                all_results.append({"error": str(r), "test_type": "across"})
                print(f"  ERROR: {r}")
            else:
                all_results.append(r)
        errors = sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, dict) and r.get("errors")))
        print(f"Completed: {len(results)} runs, {errors} with errors")

    # Save results
    runs_dir = RESULTS_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(runs_dir.glob("run*.jsonl"))
    if existing:
        last_num = int(existing[-1].name.split("_")[0].replace("run", ""))
        run_num = last_num + 1
    else:
        run_num = 1

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    output_file = runs_dir / f"run{run_num:03d}_{date_str}_opus_supplement.jsonl"
    with open(output_file, "w") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")

    elapsed_total = round(time.time() - overall_start, 1)
    total_input = sum(r.get("total_input_tokens", 0) for r in all_results)
    total_output = sum(r.get("total_output_tokens", 0) for r in all_results)
    cost = (total_input / 1_000_000 * 15) + (total_output / 1_000_000 * 75)

    print(f"\n=== Summary ===")
    print(f"Total runs: {len(all_results)}")
    print(f"Errors: {sum(1 for r in all_results if isinstance(r, dict) and r.get('errors'))}")
    print(f"Total tokens: {total_input:,} input + {total_output:,} output")
    print(f"Wall clock: {elapsed_total}s")
    print(f"Results saved to: {output_file}")
    print(f"Estimated cost: ${cost:.2f}")
    print(f"\nNext: merge with run004 JSONL and re-analyze.")


if __name__ == "__main__":
    asyncio.run(main())
