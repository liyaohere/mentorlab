"""
Generate 75 synthetic Ugandan entrepreneur profiles for agent-based simulation.

Profiles are adapted from real cohort data distributions (N=500+ refugee entrepreneurs)
but adjusted for the new cohort (general Ugandan entrepreneurs, not refugees).

Usage:
    cd backend && source .venv/bin/activate
    python scripts/generate_profiles.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add backend to path so we can read .env
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import openai

OUTPUT_PATH = Path(__file__).parent / "simulation_results" / "profiles.json"

PROFILE_GENERATION_PROMPT = """You are generating synthetic entrepreneur profiles for a research simulation.
These profiles represent general Ugandan entrepreneurs (NOT refugees) who are participating
in an AI-assisted business advisory interview.

Generate exactly {count} unique entrepreneur profiles as a JSON array.

## Distribution Requirements (based on real cohort data from Uganda)

**Business types** (approximate distribution):
- Small Business / Retail / Trading: ~40% (selling clothes, shoes, electronics, household goods at markets)
- Agriculture: ~20% (farming, fish, poultry, produce, agro-processing)
- Services: ~15% (salon/barbershop, tailoring, boda-boda transport, phone repair, catering)
- Food & Beverage: ~15% (restaurant, bakery, juice bar, street food, chapati)
- Technology / Other: ~10% (IT training, solar, digital services, manufacturing, construction)

**Locations**: Mix of urban and peri-urban Uganda:
- Kampala (40%): Owino Market, Kikuubo, Wandegeya, Kalerwe, Naalya
- Jinja (15%): Main Street, Amber Court area
- Mbale (10%): town center markets
- Gulu (15%): Gulu Main Market
- Mbarara (10%): Mbarara Central Market
- Other towns (10%): Lira, Soroti, Fort Portal

**Demographics**:
- Age: 20-45 (peak 25-35)
- Gender: ~55% male, 45% female
- Education: ~40% secondary/S6, ~25% vocational/diploma, ~25% university, ~10% primary only

**Common challenges** (vary these across profiles):
- Customer acquisition / low foot traffic
- Competition from similar businesses nearby
- Capital constraints / difficulty accessing loans
- Supply chain issues (unreliable suppliers, transport costs)
- Seasonal demand fluctuations
- Power outages affecting operations
- Managing cash flow / customers buying on credit
- Quality control / sourcing quality materials
- Scaling beyond current capacity
- Transitioning from physical to digital sales

## Output Format

Each profile must be a JSON object with exactly these fields:

```json
{{
  "id": "P001",
  "name": "Full Name",
  "age": 28,
  "gender": "Female",
  "education": "Secondary (S6)",
  "location": "Owino Market, Kampala",
  "industry_vertical": "retail",
  "intake_responses": {{
    "business_description": "...",
    "customers": "...",
    "competitors": "...",
    "revenue_source": "...",
    "main_challenge": "...",
    "current_plan": "..."
  }}
}}
```

## Critical Rules for Intake Responses

1. Write in FIRST PERSON, as if the entrepreneur is SPEAKING aloud (voice transcription style)
2. Use natural, conversational language — not formal or polished
3. Include Uganda-specific details: market names, local products (matoke, posho, chapati), UGX currency, mobile money (MTN, Airtel), local brands
4. Each answer should be 2-4 sentences long
5. The `main_challenge` and `current_plan` answers are particularly important — these are the baseline diagnostic questions. Make the challenges specific and nuanced, not generic.
6. Industry vertical must be one of: "retail", "agriculture", "services", "food_beverage", "technology"
7. IDs should be P001 through P{count:03d}
8. Each profile should have a DIFFERENT challenge — avoid repetition across profiles
9. Challenges should be complex enough that multiple causal explanations are plausible (not trivially solvable)

Return ONLY the JSON array, no other text.
"""


async def generate_profiles(count: int = 75, model: str = "gpt-4o") -> list[dict]:
    """Generate synthetic profiles using OpenAI or Anthropic."""
    use_anthropic = model.startswith("claude")

    if use_anthropic:
        import anthropic

        client = anthropic.AsyncAnthropic()
    else:
        client = openai.AsyncOpenAI()

    # Generate in 3 batches of 25 to stay within output limits
    all_profiles = []
    batch_size = 25
    for batch_num in range(0, count, batch_size):
        batch_count = min(batch_size, count - batch_num)
        start_id = batch_num + 1
        print(
            f"Generating profiles P{start_id:03d}-P{start_id + batch_count - 1:03d}..."
        )

        prompt = PROFILE_GENERATION_PROMPT.format(count=batch_count)
        # Adjust ID range instruction
        prompt += f"\n\nStart IDs from P{start_id:03d}."

        if all_profiles:
            # Provide existing profiles' industries + challenges to avoid repetition
            existing_summary = "\n".join(
                f"- {p['id']}: {p['industry_vertical']}, challenge: {p['intake_responses']['main_challenge'][:60]}..."
                for p in all_profiles[-10:]  # last 10 for context
            )
            prompt += (
                f"\n\nAlready generated (avoid similar challenges):\n{existing_summary}"
            )

        if use_anthropic:
            response = await client.messages.create(
                model=model,
                max_tokens=16000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens
        else:
            response = await client.chat.completions.create(
                model=model,
                max_tokens=16000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.choices[0].message.content.strip()
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens

        # Extract JSON array
        if "```" in text:
            # Find content between first ``` and last ```
            parts = text.split("```")
            text = parts[1] if len(parts) >= 3 else parts[-1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        try:
            batch_profiles = json.loads(text)
        except json.JSONDecodeError as e:
            # Try to salvage: find the last complete object
            print(
                f"  WARNING: JSON parse error at char {e.pos}, attempting to salvage..."
            )
            # Find the last '}' before the error and close the array
            truncated = text[: e.pos].rstrip().rstrip(",")
            # Find last complete object
            last_brace = truncated.rfind("}")
            if last_brace > 0:
                salvaged = truncated[: last_brace + 1] + "]"
                if not salvaged.startswith("["):
                    salvaged = "[" + salvaged
                batch_profiles = json.loads(salvaged)
                print(
                    f"  Salvaged {len(batch_profiles)} profiles from truncated output"
                )
            else:
                raise

        all_profiles.extend(batch_profiles)

        print(
            f"  Batch {batch_num // batch_size + 1}: {len(batch_profiles)} profiles, "
            f"{tokens_in} input / {tokens_out} output tokens"
        )

    return all_profiles


async def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Use Anthropic if key is available, otherwise OpenAI
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        model = "claude-opus-4-8"
    else:
        model = "gpt-4o"

    print("Generating 75 synthetic Ugandan entrepreneur profiles...")
    print(f"Model: {model}")
    print()

    profiles = await generate_profiles(75, model=model)

    # Validate
    industries = {}
    for p in profiles:
        v = p.get("industry_vertical", "unknown")
        industries[v] = industries.get(v, 0) + 1

    print(f"\nGenerated {len(profiles)} profiles")
    print(f"Industry distribution: {dict(sorted(industries.items()))}")

    # Save
    with open(OUTPUT_PATH, "w") as f:
        json.dump(profiles, f, indent=2)
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
