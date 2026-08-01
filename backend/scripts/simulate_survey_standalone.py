import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_simulation import (
    TokenTracker,
    simulate_survey,
    PROFILES_PATH,
    MODEL_MAP,
)


async def process_single_record(
    line: str, profiles_map: dict, model_name: str, semaphore: asyncio.Semaphore
) -> dict:
    async with semaphore:
        record = json.loads(line)

        if "result" not in record or not record.get("result", {}).get("shown"):
            return record

        profile_id = record["profile_id"]
        profile = profiles_map.get(profile_id)

        if not profile:
            record.setdefault("errors", []).append(
                f"re_eval_error: Profile {profile_id} not found in profiles.json"
            )
            return record

        shown_diagnosis = record["result"]["shown"]

        tracker = TokenTracker(model=model_name, max_tokens=600)

        try:
            new_survey = await simulate_survey(tracker, profile, shown_diagnosis)
            record["simulated_survey"] = new_survey

            new_survey_calls = tracker.pop_log()
            old_survey_calls = record.get("token_usage", {}).get("survey_call", [])

            old_in = sum(c.get("input_tokens", 0) for c in old_survey_calls)
            old_out = sum(c.get("output_tokens", 0) for c in old_survey_calls)

            new_in = sum(c.get("input_tokens", 0) for c in new_survey_calls)
            new_out = sum(c.get("output_tokens", 0) for c in new_survey_calls)

            if "token_usage" not in record:
                record["token_usage"] = {}
            record["token_usage"]["survey_call"] = new_survey_calls

            record["total_input_tokens"] = (
                record.get("total_input_tokens", 0) - old_in + new_in
            )
            record["total_output_tokens"] = (
                record.get("total_output_tokens", 0) - old_out + new_out
            )

        except Exception as e:
            record.setdefault("errors", []).append(f"survey_re_eval_error: {str(e)}")

        return record


async def main():
    parser = argparse.ArgumentParser(
        description="Re-run only the evaluation (survey) phase."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to the original .jsonl results file",
    )
    parser.add_argument(
        "--model",
        choices=["sonnet", "opus", "gpt4o", "gpt4o-mini"],
        default="gpt4o-mini",
        help="Model to use for the survey simulation",
    )
    parser.add_argument(
        "--concurrency", type=int, default=15, help="Max concurrent API calls"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found at {input_path}")
        sys.exit(1)

    if not PROFILES_PATH.exists():
        print(f"ERROR: Profiles not found at {PROFILES_PATH}")
        sys.exit(1)

    model_name = MODEL_MAP[args.model]

    print("=== MentorLab V2 Re-Evaluation (Survey Only) ===")
    print(f"Input file: {input_path.name}")
    print(f"Model: {model_name}")
    print(f"Concurrency: {args.concurrency}\n")

    with open(PROFILES_PATH, "r") as f:
        profiles_list = json.load(f)
    profiles_map = {p["id"]: p for p in profiles_list}
    print(f"Loaded {len(profiles_map)} profiles.")

    with open(input_path, "r") as f:
        lines = f.readlines()
    print(f"Found {len(lines)} records to process. Starting API calls...\n")

    start_time = time.time()
    semaphore = asyncio.Semaphore(args.concurrency)

    tasks = [
        process_single_record(line, profiles_map, model_name, semaphore)
        for line in lines
    ]
    updated_records = await asyncio.gather(*tasks)

    output_path = input_path.parent / f"{input_path.stem}_reeval.jsonl"
    with open(output_path, "w") as f:
        for record in updated_records:
            f.write(json.dumps(record) + "\n")

    elapsed = round(time.time() - start_time, 2)

    new_survey_in = 0
    new_survey_out = 0
    errors = 0
    for r in updated_records:
        if any("re_eval_error" in err for err in r.get("errors", [])):
            errors += 1
        calls = r.get("token_usage", {}).get("survey_call", [])
        new_survey_in += sum(c.get("input_tokens", 0) for c in calls)
        new_survey_out += sum(c.get("output_tokens", 0) for c in calls)

    print("\n=== Re-evaluation Summary ===")
    print(f"Records processed: {len(updated_records)}")
    print(f"New Errors: {errors}")
    print(f"Time elapsed: {elapsed} seconds")
    print(f"Survey Tokens Used: {new_survey_in:,} input + {new_survey_out:,} output")

    if "opus" in model_name:
        cost = (new_survey_in / 1_000_000 * 15) + (new_survey_out / 1_000_000 * 75)
    elif "sonnet" in model_name:
        cost = (new_survey_in / 1_000_000 * 3) + (new_survey_out / 1_000_000 * 15)
    elif "gpt-4o-mini" in model_name:
        cost = (new_survey_in / 1_000_000 * 0.15) + (new_survey_out / 1_000_000 * 0.60)
    else:  # gpt-4o
        cost = (new_survey_in / 1_000_000 * 2.50) + (new_survey_out / 1_000_000 * 10)

    print(f"Estimated Re-eval Cost: ${cost:.3f}")
    print(f"\nUpdated results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
