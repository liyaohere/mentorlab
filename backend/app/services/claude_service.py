import asyncio
import logging
from pathlib import Path

import httpx
from fastapi import HTTPException

from app.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.participant import Participant

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Maximum number of messages to include in conversation history
MAX_HISTORY_MESSAGES = 20

# Map industry vertical names to knowledge file names
INDUSTRY_KNOWLEDGE_MAP = {
    "agriculture": "agriculture",
    "retail": "retail",
    "services": "services",
    "food & beverage": "food___beverage",
    "food and beverage": "food___beverage",
    "technology": "general",
    "manufacturing": "general",
    "education": "general",
    "health": "general",
    "transport": "general",
    "other": "general",
}


class ClaudeService:
    """AI service that supports both Anthropic (Claude) and OpenAI providers."""

    def __init__(self):
        self._prompt_cache: dict[str, str] = {}

    def _load_template(self, path: str) -> str:
        if path not in self._prompt_cache:
            full_path = PROMPTS_DIR / path
            self._prompt_cache[path] = full_path.read_text()
        return self._prompt_cache[path]

    def _build_participant_context(self, participant: Participant, conversation: Conversation) -> str:
        return f"""## About This Entrepreneur
- Name: {participant.name}
- Venture: {participant.venture_name or 'Not specified'}
- Description: {participant.venture_description or 'Not specified'}
- Industry: {participant.industry_vertical or 'Not specified'}
- Week: {conversation.week_number or 1} of the program"""

    def _assemble_system_prompt(
        self,
        participant: Participant,
        conversation: Conversation,
    ) -> str:
        # 1. Arm-specific instructions
        arm_file = {
            "control": "arm1_control.md",
            "analytic": "arm2_analytic.md",
            "constructive": "arm3_constructive.md",
        }[participant.arm.value]
        arm_instructions = self._load_template(arm_file)

        # 2. Participant context
        context = self._build_participant_context(participant, conversation)

        # 3. Knowledge context (arms 2 & 3 only)
        knowledge = ""
        if participant.arm.value != "control" and participant.industry_vertical:
            slug = INDUSTRY_KNOWLEDGE_MAP.get(
                participant.industry_vertical.lower(), "general"
            )
            try:
                knowledge = self._load_template(f"shared/knowledge/{slug}.md")
            except FileNotFoundError:
                try:
                    knowledge = self._load_template("shared/knowledge/general.md")
                except FileNotFoundError:
                    knowledge = ""

        # 4. Conversation rules
        rules = self._load_template("shared/conversation_rules.md")

        parts = [arm_instructions, context]
        if knowledge:
            parts.append(knowledge)
        parts.append(rules)

        return "\n\n---\n\n".join(parts)

    def _format_messages(self, messages: list[Message]) -> list[dict]:
        formatted = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
            if msg.role.value in ("user", "assistant")
        ]
        # Limit to last MAX_HISTORY_MESSAGES
        return formatted[-MAX_HISTORY_MESSAGES:]

    async def _call_anthropic(self, system_prompt: str, messages: list[dict]) -> tuple[str, dict]:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        try:
            response = await client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=settings.CLAUDE_MAX_TOKENS,
                system=system_prompt,
                messages=messages,
            )
            text = response.content[0].text
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            return text, usage
        except anthropic.RateLimitError:
            await asyncio.sleep(2)
            response = await client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=settings.CLAUDE_MAX_TOKENS,
                system=system_prompt,
                messages=messages,
            )
            return response.content[0].text, {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise HTTPException(status_code=502, detail="AI service temporarily unavailable.")

    async def _call_openai(self, system_prompt: str, messages: list[dict]) -> tuple[str, dict]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                openai_messages = [{"role": "system", "content": system_prompt}] + messages
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json={
                        "model": settings.OPENAI_CHAT_MODEL,
                        "messages": openai_messages,
                        "max_tokens": settings.CLAUDE_MAX_TOKENS,
                    },
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                usage = {
                    "input_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("completion_tokens", 0),
                }
                return text, usage
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenAI API error: {e.response.status_code} {e.response.text}")
                if e.response.status_code == 429:
                    await asyncio.sleep(2)
                    return await self._call_openai(system_prompt, messages)
                raise HTTPException(status_code=502, detail="AI service temporarily unavailable.")
            except httpx.RequestError as e:
                logger.error(f"OpenAI connection error: {e}")
                raise HTTPException(status_code=502, detail="AI service temporarily unavailable.")

    async def _call_ai(self, system_prompt: str, messages: list[dict]) -> tuple[str, dict]:
        """Route to the configured AI provider."""
        if settings.AI_PROVIDER == "openai" or (
            not settings.ANTHROPIC_API_KEY and settings.OPENAI_API_KEY
        ):
            return await self._call_openai(system_prompt, messages)
        else:
            return await self._call_anthropic(system_prompt, messages)

    async def get_response(
        self,
        participant: Participant,
        conversation: Conversation,
        messages: list[Message],
    ) -> tuple[str, dict]:
        system_prompt = self._assemble_system_prompt(participant, conversation)
        formatted = self._format_messages(messages)
        return await self._call_ai(system_prompt, formatted)

    async def get_greeting(
        self,
        participant: Participant,
        conversation: Conversation,
    ) -> tuple[str, dict]:
        """Generate an opening message for a new conversation."""
        system_prompt = self._assemble_system_prompt(participant, conversation)
        system_prompt += "\n\n---\n\nGenerate a warm, brief opening message to start this week's conversation. If this is the first conversation, introduce yourself as their mentor. Keep it to 2-3 sentences."
        return await self._call_ai(
            system_prompt,
            [{"role": "user", "content": "Start the conversation."}],
        )


# Singleton
claude_service = ClaudeService()
