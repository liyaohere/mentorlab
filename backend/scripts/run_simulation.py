"""
Agent-based simulation harness for MentorLab V2 diagnosis pipeline.

Runs the diagnosis pipeline directly (no HTTP server / DB needed) with mock objects.
Supports within-subject (15 profiles x 3 conditions) and across-subject (60 profiles x 1 condition).

Usage:
    cd backend && source .venv/bin/activate

    # Stage 1: Sonnet dry run
    python scripts/run_simulation.py --model sonnet --test both

    # Stage 2: Opus production run
    python scripts/run_simulation.py --model opus --test both

    # Run only within-subject test
    python scripts/run_simulation.py --model sonnet --test within
"""

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from app.services.diagnosis_service import DiagnosisService

# --- Configuration ---

PROFILES_PATH = Path(__file__).parent / "simulation_results" / "profiles.json"
RESULTS_DIR = Path(__file__).parent / "simulation_results"

# Anthropic depreciated some params, including temperature.
MODEL_MAP = {
    "sonnet": "claude-sonnet-4",
    "opus": "claude-opus-4-8",
    "gpt4o": "gpt-4o",
    "gpt4o-mini": "gpt-4o-mini",
}

NEUTRAL_PROMPT = (
    "Based on what you just read, what do you think is the most important problem "
    "facing your business right now? What would you do next, and why?"
)

SURVEY_ITEMS = [
    (
        "cognitive_load",
        "How mentally demanding was it to understand the advice you received?",
    ),
    ("perceived_confusion", "How confused did you feel while reading the advice?"),
    ("trust_in_advice", "How much do you trust the advice you received?"),
    ("confidence", "How confident are you in the cause you identified?"),
    (
        "ownership",
        "How much do you feel the next steps you described are your own idea?",
    ),
    (
        "perceived_disagreement",
        "To what extent did the causes in the advice feel in tension with one another?",
    ),
    (
        "perceived_breadth",
        "To what extent did the advice cover multiple dimensions of your strategic situation?",
    ),
]

# --- Mock Objects ---


@dataclass
class MockCondition:
    value: str


@dataclass
class MockParticipant:
    id: str
    condition: MockCondition


@dataclass
class MockConversation:
    intake_responses: dict


# --- Token-tracking AI Caller ---


class TokenTracker:
    """Wraps Anthropic or OpenAI client to track tokens per call."""

    def __init__(
        self, model: str, max_tokens: int = 300, temperature: float | None = None
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.call_log: list[dict] = []
        self.use_anthropic = model.startswith("claude")

        if self.use_anthropic:
            import anthropic

            self.client = anthropic.AsyncAnthropic()
        else:
            import openai

            self.client = openai.AsyncOpenAI()

    async def call_ai(self, system_prompt: str, user_message: str) -> str:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                start = time.time()

                if self.use_anthropic:
                    extra_kwargs = (
                        {"temperature": self.temperature}
                        if self.temperature is not None
                        else {}
                    )
                    response = await self.client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_message}],
                        **extra_kwargs,
                    )
                    elapsed = time.time() - start
                    text = response.content[0].text
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                else:
                    extra_kwargs = (
                        {"temperature": self.temperature}
                        if self.temperature is not None
                        else {}
                    )
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        **extra_kwargs,
                    )
                    elapsed = time.time() - start
                    text = response.choices[0].message.content
                    input_tokens = response.usage.prompt_tokens
                    output_tokens = response.usage.completion_tokens

                self.call_log.append(
                    {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "elapsed_seconds": round(elapsed, 2),
                    }
                )

                return text

            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    wait = 2**attempt + 1
                    await asyncio.sleep(wait)
                    continue
                raise

        raise RuntimeError(f"Rate limit exceeded after {max_retries} retries")

    def pop_log(self) -> list[dict]:
        """Return and clear the call log."""
        log = self.call_log.copy()
        self.call_log.clear()
        return log


# --- Simulated Entrepreneur Agent ---


async def simulate_response(
    tracker: TokenTracker,
    profile: dict,
    diagnosis_shown: str | list[str],
    condition: str,
) -> str:
    """AI role-plays the entrepreneur responding to the neutral prompt after reading the diagnosis."""
    intake = profile["intake_responses"]
    business_context = (
        f"My business: {intake['business_description']}\n"
        f"My customers: {intake['customers']}\n"
        f"My challenge: {intake['main_challenge']}\n"
        f"My current plan: {intake['current_plan']}"
    )

    if isinstance(diagnosis_shown, list):
        advice_text = "\n\n---\n\n".join(diagnosis_shown)
        framing = "You just read THREE different analyses of your situation."
    else:
        advice_text = diagnosis_shown
        framing = "You just read an analysis of your situation."

    system_prompt = (
        f"You are {profile['name']}, a {profile.get('age', 30)}-year-old Ugandan entrepreneur "
        f"based in {profile.get('location', 'Kampala')}. {framing}\n\n"
        "Respond naturally in 3-5 sentences to the question below. "
        "Stay in character \u2014 use your own words, reference your specific business, "
        "and react authentically to what you read. Do NOT parrot the AI's exact phrasing."
    )

    user_msg = (
        f"## Your Business Context\n{business_context}\n\n"
        f"## The AI Advice You Read\n{advice_text}\n\n"
        f"## Question\n{NEUTRAL_PROMPT}"
    )

    return await tracker.call_ai(system_prompt, user_msg)


async def simulate_survey(
    tracker: TokenTracker,
    profile: dict,
    diagnosis_shown: str | list[str],
) -> dict:
    """AI role-plays the entrepreneur rating the 7 Likert survey items."""
    if isinstance(diagnosis_shown, list):
        advice_text = "\n\n---\n\n".join(diagnosis_shown)
    else:
        advice_text = diagnosis_shown
    framing = "an analysis"

    items_text = "\n".join(f'  "{key}": <1-7>  // {desc}' for key, desc in SURVEY_ITEMS)

    system_prompt = (
        f"You are {profile['name']}, a Ugandan entrepreneur. "
        f"You just read {framing} of your business situation.\n\n"
        "Rate each item on a scale of 1 (not at all) to 7 (extremely). "
        "Be realistic and thoughtful."
        "Return ONLY valid JSON, no other text."
    )

    user_msg = (
        f"## The Advice You Read\n{advice_text}\n\n"
        f"## Rate These Items (1-7)\n{{\n{items_text}\n}}"
    )

    response_text = await tracker.call_ai(system_prompt, user_msg)

    # Parse JSON from response
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"parse_error": text}


# --- Single Pipeline Run ---


async def run_single(
    profile: dict,
    condition: str,
    mentor_tracker: TokenTracker,
    participant_tracker: TokenTracker,
    semaphore: asyncio.Semaphore,
    run_id: str,
    test_type: str,
) -> dict:
    """Run one complete simulation: diagnosis + simulated response + simulated survey.

    mentor_tracker drives the mentor/diagnosis pipeline (temperature configurable via
    --temperature). participant_tracker drives the simulated participant (survey ratings
    and free-text responses) and always uses the API default temperature, independent of
    --temperature.
    """
    async with semaphore:
        start = time.time()
        errors = []

        # Create mock objects
        participant = MockParticipant(
            id=profile["id"],
            condition=MockCondition(value=condition),
        )
        conversation = MockConversation(
            intake_responses=profile["intake_responses"],
        )

        # Create a fresh DiagnosisService with our mentor tracker
        service = DiagnosisService(ai_caller=mentor_tracker.call_ai)

        # Run the diagnosis pipeline
        try:
            result = await service.generate_diagnosis(participant, conversation)
        except Exception as e:
            errors.append(f"diagnosis_error: {str(e)}")
            return {
                "run_id": run_id,
                "test_type": test_type,
                "profile_id": profile["id"],
                "condition": condition,
                "errors": errors,
                "wall_clock_seconds": round(time.time() - start, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        diagnosis_calls = mentor_tracker.pop_log()

        # Get what was shown
        shown = result.get("shown", "")

        # Simulate entrepreneur's response
        try:
            sim_response = await simulate_response(
                participant_tracker, profile, shown, condition
            )
        except Exception as e:
            sim_response = None
            errors.append(f"response_sim_error: {str(e)}")

        response_calls = participant_tracker.pop_log()

        # Simulate survey
        try:
            sim_survey = await simulate_survey(participant_tracker, profile, shown)
        except Exception as e:
            sim_survey = None
            errors.append(f"survey_sim_error: {str(e)}")

        survey_calls = participant_tracker.pop_log()

        elapsed = round(time.time() - start, 2)

        # Compute totals
        all_calls = diagnosis_calls + response_calls + survey_calls
        total_input = sum(c["input_tokens"] for c in all_calls)
        total_output = sum(c["output_tokens"] for c in all_calls)

        return {
            "run_id": run_id,
            "test_type": test_type,
            "profile_id": profile["id"],
            "condition": condition,
            "result": {
                "type": result.get("type"),
                "orchestrator_causes": result.get("orchestrator_causes"),
                "raw_diagnoses": result.get("raw_diagnoses"),
                "integrated": result.get("integrated"),
                "shown": shown,
                "divergence_check": result.get("divergence_check"),
            },
            "simulated_response": sim_response,
            "simulated_survey": sim_survey,
            "token_usage": {
                "diagnosis_calls": diagnosis_calls,
                "response_call": response_calls,
                "survey_call": survey_calls,
            },
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "wall_clock_seconds": elapsed,
            "errors": errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# --- Test Runners ---


async def run_within_subject(
    profiles: list[dict],
    mentor_tracker: TokenTracker,
    participant_tracker: TokenTracker,
    concurrency: int,
) -> list[dict]:
    within_profiles = profiles[:30]
    conditions = ["single", "integrated", "competing"]
    semaphore = asyncio.Semaphore(concurrency)

    tasks = []
    for profile in within_profiles:
        for cond in conditions:
            run_id = f"within_{profile['id']}_{cond}"
            tasks.append(
                run_single(
                    profile,
                    cond,
                    mentor_tracker,
                    participant_tracker,
                    semaphore,
                    run_id,
                    "within",
                )
            )

    print(
        f"Running {len(tasks)} within-subject pipeline runs (concurrency={concurrency})..."
    )
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    final = []
    for r in results:
        if isinstance(r, Exception):
            final.append({"error": str(r), "test_type": "within"})
        else:
            final.append(r)

    return final


async def run_across_subject(
    profiles: list[dict],
    mentor_tracker: TokenTracker,
    participant_tracker: TokenTracker,
    concurrency: int,
) -> list[dict]:
    across_profiles = profiles[0:150]

    # Stratified randomization by industry_vertical
    by_industry: dict[str, list[dict]] = {}
    for p in across_profiles:
        v = p.get("industry_vertical", "other")
        by_industry.setdefault(v, []).append(p)

    conditions = ["single", "integrated", "competing"]
    assigned: list[tuple[dict, str]] = []

    for _, industry_profiles in by_industry.items():
        for i, p in enumerate(industry_profiles):
            cond = conditions[i % 3]
            assigned.append((p, cond))

    semaphore = asyncio.Semaphore(concurrency)
    tasks = []
    for profile, cond in assigned:
        run_id = f"across_{profile['id']}_{cond}"
        tasks.append(
            run_single(
                profile,
                cond,
                mentor_tracker,
                participant_tracker,
                semaphore,
                run_id,
                "across",
            )
        )

    # Print assignment summary
    cond_counts = {}
    for _, cond in assigned:
        cond_counts[cond] = cond_counts.get(cond, 0) + 1
    print(
        f"Running {len(tasks)} across-subject pipeline runs: {cond_counts} (concurrency={concurrency})"
    )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    final = []
    for r in results:
        if isinstance(r, Exception):
            final.append({"error": str(r), "test_type": "across"})
        else:
            final.append(r)

    return final


# --- Main ---


async def main():
    parser = argparse.ArgumentParser(description="MentorLab V2 Simulation")
    parser.add_argument(
        "--model",
        choices=["sonnet", "opus", "gpt4o", "gpt4o-mini"],
        default="gpt4o",
        help="Model to use for diagnosis pipeline",
    )
    parser.add_argument(
        "--test",
        choices=["within", "across", "both"],
        default="both",
        help="Which test to run",
    )
    parser.add_argument(
        "--concurrency", type=int, default=10, help="Max concurrent API calls"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help=(
            "Sampling temperature for the simulated mentor / diagnosis pipeline only. "
            "Does NOT affect the simulated participant (survey ratings, free-text "
            "responses), which always uses the API default temperature. "
            "If omitted, the mentor also uses the API default."
        ),
    )
    args = parser.parse_args()

    model = MODEL_MAP[args.model]
    print(f"=== MentorLab V2 Simulation ===")
    print(f"Model: {model}")
    print(f"Test: {args.test}")
    print(f"Concurrency: {args.concurrency}")
    print(
        f"Mentor temperature: {args.temperature if args.temperature is not None else 'default'}"
    )
    print()

    # Load profiles
    if not PROFILES_PATH.exists():
        print(f"ERROR: Profiles not found at {PROFILES_PATH}")
        print("Run: python scripts/generate_profiles.py")
        sys.exit(1)

    with open(PROFILES_PATH) as f:
        profiles = json.load(f)
    print(f"Loaded {len(profiles)} profiles")

    if len(profiles) < 75:
        print(f"WARNING: Expected 75 profiles, got {len(profiles)}")

    # mentor_tracker drives the simulated mentor / diagnosis pipeline; its temperature
    # is controlled by --temperature. participant_tracker drives the simulated
    # participant (survey + free-text response) and is intentionally left at the API
    # default temperature regardless of --temperature.
    mentor_tracker = TokenTracker(
        model=model, max_tokens=600, temperature=args.temperature
    )
    participant_tracker = TokenTracker(model=model, max_tokens=600)
    all_results = []
    overall_start = time.time()

    # Run tests
    if args.test in ("within", "both"):
        print(f"\n--- Test A: Within-Subject ---")
        within_results = await run_within_subject(
            profiles, mentor_tracker, participant_tracker, args.concurrency
        )
        all_results.extend(within_results)

        # Quick summary
        errors = sum(1 for r in within_results if r.get("errors"))
        print(f"Completed: {len(within_results)} runs, {errors} with errors")

    if args.test in ("across", "both"):
        print(f"\n--- Test B: Across-Subject ---")
        across_results = await run_across_subject(
            profiles, mentor_tracker, participant_tracker, args.concurrency
        )
        all_results.extend(across_results)

        errors = sum(1 for r in across_results if r.get("errors"))
        print(f"Completed: {len(across_results)} runs, {errors} with errors")

    # Save results with versioned filename
    runs_dir = RESULTS_DIR / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Auto-increment run number
    existing = sorted(runs_dir.glob("run*.jsonl"))
    if existing:
        last_num = int(existing[-1].name.split("_")[0].replace("run", ""))
        run_num = last_num + 1
    else:
        run_num = 1

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    output_file = (
        runs_dir / f"run{run_num:03d}_{date_str}_{args.model}_{args.test}.jsonl"
    )
    with open(output_file, "w") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")

    elapsed_total = round(time.time() - overall_start, 1)

    # Print summary
    total_input = sum(r.get("total_input_tokens", 0) for r in all_results)
    total_output = sum(r.get("total_output_tokens", 0) for r in all_results)
    total_errors = sum(1 for r in all_results if r.get("errors"))

    print(f"\n=== Summary ===")
    print(f"Total runs: {len(all_results)}")
    print(f"Errors: {total_errors}")
    print(f"Total tokens: {total_input:,} input + {total_output:,} output")
    print(f"Wall clock: {elapsed_total}s")
    print(f"Results saved to: {output_file}")

    # Cost estimate
    if "opus" in model:
        cost = (total_input / 1_000_000 * 15) + (total_output / 1_000_000 * 75)
    elif "sonnet" in model:
        cost = (total_input / 1_000_000 * 3) + (total_output / 1_000_000 * 15)
    elif "gpt-4o-mini" in model:
        cost = (total_input / 1_000_000 * 0.15) + (total_output / 1_000_000 * 0.60)
    else:  # gpt-4o
        cost = (total_input / 1_000_000 * 2.50) + (total_output / 1_000_000 * 10)
    print(f"Estimated cost: ${cost:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
