"""
Generate 45 additional synthetic profiles (P076-P120) and append to profiles.json.

- P076-P090 (15 profiles): for within-subject appendix supplement
- P091-P120 (30 profiles): for between-subject supplement (to reach 30/30/30)

Usage:
    cd backend && source .venv/bin/activate
    python scripts/generate_profiles_supplement.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

PROFILES_PATH = Path(__file__).parent / "simulation_results" / "profiles.json"

PROFILE_GENERATION_PROMPT = """You are generating synthetic entrepreneur profiles for a research simulation.
These profiles represent general Ugandan entrepreneurs (NOT refugees) who are participating
in an AI-assisted business advisory interview.

Generate exactly {count} unique entrepreneur profiles as a JSON array.

## Distribution Requirements (based on real cohort data from Uganda)

**Business types** (approximate distribution):
- Small Business / Retail / Trading: ~40%
- Agriculture: ~20%
- Services: ~15%
- Food & Beverage: ~15%
- Technology / Other: ~10%

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

## Output Format

Each profile must be a JSON object with exactly these fields:

```json
{{
  "id": "P076",
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
5. The `main_challenge` and `current_plan` answers are particularly important — make challenges specific and nuanced
6. Industry vertical must be one of: "retail", "agriculture", "services", "food_beverage", "technology"
7. Each profile should have a DIFFERENT challenge — avoid repetition
8. Challenges should be complex enough that multiple causal explanations are plausible

Return ONLY the JSON array, no other text.
"""


async def generate_supplement():
    import anthropic
    client = anthropic.AsyncAnthropic(timeout=httpx.Timeout(600.0, connect=10.0))
    model = "claude-opus-4-20250514"

    # Load existing profiles to avoid repetition
    with open(PROFILES_PATH) as f:
        existing = json.load(f)
    print(f"Loaded {len(existing)} existing profiles")

    existing_summary = "\n".join(
        f"- {p['id']}: {p['industry_vertical']}, {p.get('location','')}, challenge: {p['intake_responses']['main_challenge'][:80]}..."
        for p in existing[-20:]
    )

    new_profiles = []
    # Generate in 3 batches of 15
    for batch_idx in range(3):
        start_id = 76 + batch_idx * 15
        end_id = start_id + 14
        count = 15
        print(f"\nGenerating P{start_id:03d}-P{end_id:03d}...")

        prompt = PROFILE_GENERATION_PROMPT.format(count=count)
        prompt += f"\n\nStart IDs from P{start_id:03d} through P{end_id:03d}."
        prompt += f"\n\nAlready generated (avoid similar challenges and locations):\n{existing_summary}"

        if new_profiles:
            new_summary = "\n".join(
                f"- {p['id']}: {p['industry_vertical']}, challenge: {p['intake_responses']['main_challenge'][:60]}..."
                for p in new_profiles
            )
            prompt += f"\n\nAlso just generated in this session:\n{new_summary}"

        response = await client.messages.create(
            model=model,
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Extract JSON
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) >= 3 else parts[-1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        try:
            batch = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"  WARNING: JSON parse error, salvaging...")
            truncated = text[:e.pos].rstrip().rstrip(",")
            last_brace = truncated.rfind("}")
            if last_brace > 0:
                salvaged = truncated[:last_brace + 1] + "]"
                if not salvaged.startswith("["):
                    salvaged = "[" + salvaged
                batch = json.loads(salvaged)
            else:
                raise

        new_profiles.extend(batch)
        print(f"  Got {len(batch)} profiles ({response.usage.input_tokens} in / {response.usage.output_tokens} out)")

    # Append to existing
    all_profiles = existing + new_profiles
    with open(PROFILES_PATH, "w") as f:
        json.dump(all_profiles, f, indent=2)

    # Validate
    industries = {}
    for p in new_profiles:
        v = p.get("industry_vertical", "unknown")
        industries[v] = industries.get(v, 0) + 1

    print(f"\nGenerated {len(new_profiles)} new profiles (P076-P{75+len(new_profiles):03d})")
    print(f"Industry distribution: {dict(sorted(industries.items()))}")
    print(f"Total profiles now: {len(all_profiles)}")
    print(f"Saved to {PROFILES_PATH}")


if __name__ == "__main__":
    asyncio.run(generate_supplement())
