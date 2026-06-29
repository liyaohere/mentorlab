"""
Diagnosis Service: Sequential multi-agent pipeline for generating competing causal diagnoses.

Architecture (from V6 design doc):
  Orchestrator → Agent A → Agent B (reads A) → Agent C (reads A+B) → Divergence Check

For Condition 1 (single): Orchestrator + Agent A only
For Condition 2 (integrated): Full pipeline + Integrator
For Condition 3 (competing): Full pipeline, all 3 shown
"""

import logging
from pathlib import Path

from app.models.conversation import Conversation
from app.models.participant import Participant

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
MAX_RETRY_ATTEMPTS = 2


def _load_prompt(path: str) -> str:
    return (PROMPTS_DIR / path).read_text()


INTAKE_QUESTION_LABELS = {
    "business_description": "What does your business do? What do you sell or make?",
    "customers": "Who are your main customers?",
    "competitors": "Do you have competitors? Tell me about them.",
    "revenue_source": "Where does your money come from?",
    "main_challenge": "What is the biggest problem or challenge your business is facing right now?",
    "current_plan": "What is your current plan for dealing with this challenge, and why?",
}


def _format_intake_summary(conversation: Conversation) -> str:
    """Format intake responses into a readable summary for agent prompts."""
    responses = conversation.intake_responses or {}
    parts = []
    for key, answer in responses.items():
        question = INTAKE_QUESTION_LABELS.get(key, key)
        if answer:  # Skip empty answers
            parts.append(f"Q: {question}\nA: {answer}")
    return "\n\n".join(parts)


def _build_agent_prompt(
    cause_statement: str,
    intake_summary: str,
    prior_diagnoses: list[str],
    agent_index: int,
) -> str:
    """Build a complete agent prompt from the template, parameterized per agent."""
    template = _load_prompt("agents/agent_template.md")

    if agent_index == 0:
        disagreement_instruction = ""
    elif agent_index == 1:
        disagreement_instruction = (
            "## Important: You DISAGREE with the previous advisor\n\n"
            "You have read a previous advisor's diagnosis (below). You DISAGREE with their reading. "
            "Before presenting your own diagnosis, explain briefly (1 sentence) why their reading "
            "misses the real issue.\n\n"
            f"### Previous Diagnosis:\n{prior_diagnoses[0]}"
        )
    elif agent_index == 2:
        disagreement_instruction = (
            "## Important: You DISAGREE WITH BOTH previous advisors\n\n"
            "You have read two previous advisors' diagnoses (below). You DISAGREE WITH BOTH. "
            "Before presenting your own diagnosis, explain briefly (1-2 sentences) why both "
            "readings miss the real issue.\n\n"
            f"### Previous Diagnosis 1:\n{prior_diagnoses[0]}\n\n"
            f"### Previous Diagnosis 2:\n{prior_diagnoses[1]}"
        )
    else:
        disagreement_instruction = ""

    return template.format(
        cause_statement=cause_statement,
        intake_summary=intake_summary,
        disagreement_instruction=disagreement_instruction,
    )


class DiagnosisService:
    def __init__(self, ai_caller):
        """
        Args:
            ai_caller: async function(system_prompt: str, user_message: str) -> str
                       Wraps claude_service or openai call. Returns text response.
        """
        self._call_ai = ai_caller

    async def run_orchestrator(self, intake_summary: str) -> list[str]:
        """Analyze intake and identify 3 action-incompatible causal directions."""
        system_prompt = _load_prompt("agents/orchestrator.md")
        user_msg = f"Here is the entrepreneur's intake interview:\n\n{intake_summary}"

        response = await self._call_ai(system_prompt, user_msg)

        # Parse "Cause A: ...\nCause B: ...\nCause C: ..."
        causes = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("Cause"):
                # Remove "Cause A: " prefix
                cause_text = line.split(":", 1)[1].strip() if ":" in line else line
                causes.append(cause_text)

        if len(causes) < 3:
            logger.warning(
                f"Orchestrator returned {len(causes)} causes, expected 3. Raw: {response}"
            )
            # Pad with empty if needed (will likely fail divergence check)
            while len(causes) < 3:
                causes.append("Unable to generate additional cause.")

        return causes[:3]

    async def run_agent(
        self,
        cause_statement: str,
        intake_summary: str,
        prior_diagnoses: list[str],
        agent_index: int,
    ) -> str:
        """Generate a single agent's diagnosis."""
        system_prompt = _build_agent_prompt(
            cause_statement=cause_statement,
            intake_summary=intake_summary,
            prior_diagnoses=prior_diagnoses,
            agent_index=agent_index,
        )
        user_msg = "Please generate your diagnosis now."
        return await self._call_ai(system_prompt, user_msg)

    async def run_divergence_check(
        self,
        diagnosis_a: str,
        diagnosis_b: str,
        diagnosis_c: str,
    ) -> str:
        """Verify diagnoses are genuinely action-incompatible. Returns 'PASS' or 'FAIL: reason'."""
        system_prompt = _load_prompt("agents/divergence_checker.md")
        user_msg = (
            f"Diagnosis 1:\n{diagnosis_a}\n\n"
            f"Diagnosis 2:\n{diagnosis_b}\n\n"
            f"Diagnosis 3:\n{diagnosis_c}"
        )
        response = await self._call_ai(system_prompt, user_msg)
        return response.strip()

    async def run_integrator(
        self,
        diagnosis_a: str,
        diagnosis_b: str,
        diagnosis_c: str,
    ) -> str:
        """Synthesize 3 diagnoses into 1 coherent recommendation (Condition 2 only)."""
        system_prompt = _load_prompt("agents/integrator.md")
        user_msg = (
            f"Diagnosis 1 (One reading):\n{diagnosis_a}\n\n"
            f"Diagnosis 2 (A different reading):\n{diagnosis_b}\n\n"
            f"Diagnosis 3 (A third possibility):\n{diagnosis_c}"
        )
        return await self._call_ai(system_prompt, user_msg)

    async def run_summarizer(
        self,
        diagnosis_a: str,
        diagnosis_b: str,
        diagnosis_c: str,
    ) -> list[str]:
        """Condense 3 diagnoses while preserving disagreement (Condition 3 only)."""
        system_prompt = _load_prompt("agents/summarizer.md")
        user_msg = (
            f"Diagnosis 1:\n{diagnosis_a}\n\n"
            f"Diagnosis 2:\n{diagnosis_b}\n\n"
            f"Diagnosis 3:\n{diagnosis_c}"
        )
        response = await self._call_ai(system_prompt, user_msg)

        # Split on "---" separator
        parts = [p.strip() for p in response.split("---") if p.strip()]
        if len(parts) == 3:
            return parts
        # Fallback: return as single list if separator parsing fails
        logger.warning(
            f"Summarizer returned {len(parts)} parts, expected 3. Using raw split."
        )
        return parts if parts else [response]

    async def generate_diagnosis(
        self,
        participant: Participant,
        conversation: Conversation,
    ) -> dict:
        """
        Main entry point. Routes by participant condition.

        Returns:
            {
                "type": "single" | "integrated" | "competing",
                "orchestrator_causes": [str, str, str],
                "raw_diagnoses": [str] or [str, str, str],
                "integrated": str | None,
                "shown": str | [str, str, str],
                "divergence_check": str | None,
            }
        """
        intake_summary = _format_intake_summary(conversation)
        condition = participant.condition.value if participant.condition else "single"

        # Step 1: Orchestrator identifies 3 causal directions
        causes = await self.run_orchestrator(intake_summary)
        logger.info(f"Orchestrator identified causes for {participant.id}: {causes}")

        # Step 2: Agent A (always runs)
        diagnosis_a = await self.run_agent(causes[0], intake_summary, [], agent_index=0)

        if condition == "single":
            # C1: Only Agent A
            return {
                "type": "single",
                "orchestrator_causes": causes,
                "raw_diagnoses": [diagnosis_a],
                "integrated": None,
                "shown": diagnosis_a,
                "divergence_check": None,
            }

        # C2 and C3: Full sequential pipeline
        # Step 3: Agent B (reads A)
        diagnosis_b = await self.run_agent(
            causes[1], intake_summary, [diagnosis_a], agent_index=1
        )

        # Step 4: Agent C (reads A + B)
        diagnosis_c = await self.run_agent(
            causes[2], intake_summary, [diagnosis_a, diagnosis_b], agent_index=2
        )

        # Step 5: Divergence check
        check_result = await self.run_divergence_check(
            diagnosis_a, diagnosis_b, diagnosis_c
        )
        logger.info(f"Divergence check for {participant.id}: {check_result}")

        if check_result.startswith("FAIL") and MAX_RETRY_ATTEMPTS > 0:
            # Retry once from orchestrator
            logger.warning(f"Divergence check failed, retrying. Reason: {check_result}")
            causes = await self.run_orchestrator(intake_summary)
            diagnosis_a = await self.run_agent(
                causes[0], intake_summary, [], agent_index=0
            )
            diagnosis_b = await self.run_agent(
                causes[1], intake_summary, [diagnosis_a], agent_index=1
            )
            diagnosis_c = await self.run_agent(
                causes[2], intake_summary, [diagnosis_a, diagnosis_b], agent_index=2
            )
            check_result = await self.run_divergence_check(
                diagnosis_a, diagnosis_b, diagnosis_c
            )

        raw_diagnoses = [diagnosis_a, diagnosis_b, diagnosis_c]

        if condition == "integrated":
            # C2: Integrate into single recommendation
            integrated = await self.run_integrator(
                diagnosis_a, diagnosis_b, diagnosis_c
            )
            return {
                "type": "integrated",
                "orchestrator_causes": causes,
                "raw_diagnoses": raw_diagnoses,
                "integrated": integrated,
                "shown": integrated,
                "divergence_check": check_result,
            }
        else:
            # C3: Summarize (compress but preserve disagreement)
            summarized = await self.run_summarizer(
                diagnosis_a, diagnosis_b, diagnosis_c
            )
            return {
                "type": "competing",
                "orchestrator_causes": causes,
                "raw_diagnoses": raw_diagnoses,
                "integrated": None,
                "shown": summarized,
                "divergence_check": check_result,
            }
