"""
V2 Interview Router: Handles the full interview flow for the competing diagnoses experiment.

Flow: intake → baseline → diagnosis generation → diagnosis display → neutral response → survey
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from fastapi.responses import Response

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_participant
from app.models.conversation import Conversation, ConversationStatus, InitiatorType
from app.models.participant import ConditionType, Participant
from app.services.claude_service import claude_service
from app.services.diagnosis_service import DiagnosisService
from app.services.tts_service import tts_service

# Map arm types to v2 conditions
ARM_TO_CONDITION = {
    "c1": ConditionType.single,
    "c2": ConditionType.integrated,
    "c3": ConditionType.competing,
}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/interview", tags=["interview"])

# --- Request/Response Models ---


class StartInterviewResponse(BaseModel):
    conversation_id: str
    first_question: str
    status: str
    condition: str | None = None


class IntakeAnswerRequest(BaseModel):
    answer: str
    question_index: int


class IntakeAnswerResponse(BaseModel):
    next_question: str | None
    intake_complete: bool
    status: str


class DiagnosisResponse(BaseModel):
    type: str  # "single" | "integrated" | "competing"
    diagnoses: list[str]  # 1 for single/integrated, 3 for competing
    labels: list[str]  # labels for each diagnosis
    response_prompt: str


class SelectionRequest(BaseModel):
    choice: int  # 0, 1, or 2


class ResponseRequest(BaseModel):
    text: str
    reading_time_seconds: int | None = None
    writing_time_seconds: int | None = None


class SurveyRequest(BaseModel):
    cognitive_load: float
    perceived_confusion: float
    trust_in_advice: float
    confidence: float
    ownership: float
    # Manipulation checks
    perceived_disagreement: float | None = None
    perceived_breadth: float | None = None


# --- Intake Questions ---

INTAKE_QUESTIONS = [
    "Welcome! I'd like to learn about your business. Can you tell me — what does your business do? What do you sell or make?",
    "Who are your main customers? Who buys from you most often?",
    "Do you have competitors — other people or businesses that sell similar things? Tell me about them.",
    "Where does your money come from? What is your main source of revenue?",
    # Baseline questions (embedded at end)
    "What is the biggest problem or challenge your business is facing right now?",
    "What is your current plan for dealing with this challenge? And why do you think that's the right approach?",
]

INTAKE_QUESTION_KEYS = [
    "business_description",
    "customers",
    "competitors",
    "revenue_source",
    "main_challenge",  # baseline Q1
    "current_plan",  # baseline Q2
]

NEUTRAL_RESPONSE_PROMPT = (
    "Based on what you just read, what do you think is the most important problem "
    "facing your business right now? What would you do next, and why?"
)


# --- AI Caller wrapper ---


async def _call_ai(system_prompt: str, user_message: str) -> str:
    """Wrapper for diagnosis_service: calls AI with a system prompt + user message."""
    text, _ = await claude_service._call_ai(
        system_prompt,
        [{"role": "user", "content": user_message}],
    )
    return text


diagnosis_service = DiagnosisService(ai_caller=_call_ai)


# --- Endpoints ---


@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Start a new v2 interview session."""
    # Auto-set condition from arm if not already set
    if not participant.condition and participant.arm:
        participant.condition = ARM_TO_CONDITION.get(
            participant.arm.value, ConditionType.single
        )
        await db.flush()

    conversation = Conversation(
        participant_id=participant.id,
        initiated_by=InitiatorType.system,
        status=ConversationStatus.intake,
        intake_complete=False,
        intake_responses={},
        intake_question_index=0,
        title="AI Interview Session",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return StartInterviewResponse(
        conversation_id=str(conversation.id),
        first_question=INTAKE_QUESTIONS[0],
        status="intake",
        condition=participant.condition.value if participant.condition else None,
    )


@router.post("/{conversation_id}/intake", response_model=IntakeAnswerResponse)
async def submit_intake_answer(
    conversation_id: uuid.UUID,
    request: IntakeAnswerRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Submit an answer to the current intake question."""
    conversation = await _get_conversation(conversation_id, participant.id, db)

    if conversation.status not in (
        ConversationStatus.intake,
        ConversationStatus.baseline,
    ):
        raise HTTPException(status_code=400, detail="Interview is not in intake phase")

    # Store the answer — must create new dict for SQLAlchemy JSON mutation detection
    responses = dict(conversation.intake_responses or {})
    key = INTAKE_QUESTION_KEYS[request.question_index]
    responses[key] = request.answer
    conversation.intake_responses = responses
    flag_modified(conversation, "intake_responses")
    conversation.intake_question_index = request.question_index + 1

    # Check if we're entering baseline phase (questions 5-6)
    if request.question_index == 3:  # Just finished last factual question
        conversation.status = ConversationStatus.baseline

    # Check if intake is complete
    if request.question_index >= len(INTAKE_QUESTIONS) - 1:
        conversation.intake_complete = True
        conversation.baseline_responses = {
            "main_challenge": responses.get("main_challenge", ""),
            "current_plan": responses.get("current_plan", ""),
        }
        conversation.status = ConversationStatus.analyzing

        await db.commit()

        return IntakeAnswerResponse(
            next_question=None,
            intake_complete=True,
            status="analyzing",
        )

    next_q = INTAKE_QUESTIONS[request.question_index + 1]
    await db.commit()

    return IntakeAnswerResponse(
        next_question=next_q,
        intake_complete=False,
        status=conversation.status.value,
    )


@router.post("/{conversation_id}/generate-diagnosis", response_model=DiagnosisResponse)
async def generate_diagnosis(
    conversation_id: uuid.UUID,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Trigger diagnosis generation after intake is complete."""
    conversation = await _get_conversation(conversation_id, participant.id, db)

    if not conversation.intake_complete:
        raise HTTPException(status_code=400, detail="Intake not yet complete")
    if conversation.diagnosis_raw is not None:
        raise HTTPException(status_code=400, detail="Diagnosis already generated")

    # Run the diagnosis pipeline
    result = await diagnosis_service.generate_diagnosis(participant, conversation)

    # Store results
    conversation.orchestrator_output = result["orchestrator_causes"]
    conversation.diagnosis_raw = result["raw_diagnoses"]
    conversation.diagnosis_integrated = result.get("integrated")
    conversation.diagnosis_shown = (
        result["shown"]
        if isinstance(result["shown"], str)
        else "\n---\n".join(result["shown"])
    )
    # Store just PASS/FAIL (column is VARCHAR(10)); full message is in server logs
    dc = result.get("divergence_check") or ""
    conversation.divergence_check = (
        "PASS" if dc.startswith("PASS") else "FAIL" if dc else None
    )
    conversation.status = ConversationStatus.diagnosis

    await db.commit()

    # Format response for frontend
    if result["type"] == "single":
        return DiagnosisResponse(
            type="single",
            diagnoses=[result["shown"]],
            labels=["Our analysis of your situation:"],
            response_prompt=NEUTRAL_RESPONSE_PROMPT,
        )
    elif result["type"] == "integrated":
        return DiagnosisResponse(
            type="integrated",
            diagnoses=[result["shown"]],
            labels=["Our analysis of your situation:"],
            response_prompt=NEUTRAL_RESPONSE_PROMPT,
        )
    else:  # competing
        # Use summarized (shortened) versions for display; raw_diagnoses stored in DB
        shown = (
            result["shown"] if isinstance(result["shown"], list) else [result["shown"]]
        )
        return DiagnosisResponse(
            type="competing",
            diagnoses=shown,
            labels=[
                "One reading of your situation:",
                "A different reading:",
                "A third possibility:",
            ],
            response_prompt=NEUTRAL_RESPONSE_PROMPT,
        )


@router.post("/{conversation_id}/selection")
async def submit_selection(
    conversation_id: uuid.UUID,
    request: SelectionRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """C3 only: Record which diagnosis the entrepreneur selected as closest."""
    conversation = await _get_conversation(conversation_id, participant.id, db)
    conversation.selection_choice = request.choice
    await db.commit()
    return {"status": "ok"}


@router.post("/{conversation_id}/response")
async def submit_response(
    conversation_id: uuid.UUID,
    request: ResponseRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Submit the entrepreneur's response to the neutral prompt (PRIMARY DV)."""
    conversation = await _get_conversation(conversation_id, participant.id, db)
    conversation.response_text = request.text
    conversation.response_created_at = datetime.now(timezone.utc)
    conversation.reading_time_seconds = request.reading_time_seconds
    conversation.writing_time_seconds = request.writing_time_seconds
    conversation.status = ConversationStatus.survey
    await db.commit()
    return {"status": "ok", "next": "survey"}


@router.post("/{conversation_id}/survey")
async def submit_survey(
    conversation_id: uuid.UUID,
    request: SurveyRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Submit process measures (cognitive load, trust, etc.)."""
    conversation = await _get_conversation(conversation_id, participant.id, db)
    conversation.cognitive_load_score = request.cognitive_load
    conversation.perceived_confusion_score = request.perceived_confusion
    conversation.trust_in_advice_score = request.trust_in_advice
    conversation.confidence_score = request.confidence
    conversation.ownership_score = request.ownership
    conversation.perceived_disagreement_score = request.perceived_disagreement
    conversation.perceived_breadth_score = request.perceived_breadth
    conversation.status = ConversationStatus.complete
    conversation.ended_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "complete"}


@router.get("/{conversation_id}/transcript")
async def get_transcript(
    conversation_id: uuid.UUID,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Download the full session transcript."""
    conversation = await _get_conversation(conversation_id, participant.id, db)
    return {
        "intake": conversation.intake_responses,
        "baseline": conversation.baseline_responses,
        "diagnosis_type": "competing"
        if conversation.diagnosis_raw and len(conversation.diagnosis_raw) == 3
        else "single",
        "diagnoses": conversation.diagnosis_raw,
        "integrated": conversation.diagnosis_integrated,
        "selection_choice": conversation.selection_choice,
        "response": conversation.response_text,
        "survey": {
            "cognitive_load": conversation.cognitive_load_score,
            "perceived_confusion": conversation.perceived_confusion_score,
            "trust_in_advice": conversation.trust_in_advice_score,
            "confidence": conversation.confidence_score,
            "ownership": conversation.ownership_score,
            "perceived_disagreement": conversation.perceived_disagreement_score,
            "perceived_breadth": conversation.perceived_breadth_score,
        },
    }


@router.get("/admin/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint: list all v2 interview sessions with key data."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.intake_responses.isnot(None))
        .order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()

    sessions = []
    for c in conversations:
        # Get participant info
        p_result = await db.execute(
            select(Participant).where(Participant.id == c.participant_id)
        )
        p = p_result.scalar_one_or_none()

        condition = p.condition.value if p and p.condition else None
        if not condition and p and p.arm:
            condition = ARM_TO_CONDITION.get(p.arm.value, ConditionType.single).value

        sessions.append(
            {
                "id": str(c.id),
                "participant": p.name if p else "Unknown",
                "condition": condition,
                "status": c.status.value,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "has_diagnoses": c.diagnosis_raw is not None,
                "has_response": c.response_text is not None,
                "selection_choice": c.selection_choice,
                "survey_complete": c.cognitive_load_score is not None,
            }
        )

    return {"sessions": sessions}


@router.get("/admin/session/{conversation_id}")
async def get_session_detail(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint: get full session data for analysis."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Session not found")

    p_result = await db.execute(
        select(Participant).where(Participant.id == c.participant_id)
    )
    p = p_result.scalar_one_or_none()

    return {
        "session_id": str(c.id),
        "participant": {
            "name": p.name if p else None,
            "condition": p.condition.value if p and p.condition else None,
            "arm": p.arm.value if p and p.arm else None,
            "venture": p.venture_name if p else None,
        },
        "status": c.status.value,
        "intake": c.intake_responses,
        "baseline": c.baseline_responses,
        "orchestrator_causes": c.orchestrator_output,
        "diagnoses_raw": c.diagnosis_raw,
        "diagnosis_integrated": c.diagnosis_integrated,
        "diagnosis_shown": c.diagnosis_shown,
        "divergence_check": c.divergence_check,
        "selection_choice": c.selection_choice,
        "response_text": c.response_text,
        "timing": {
            "reading_seconds": c.reading_time_seconds,
            "writing_seconds": c.writing_time_seconds,
        },
        "survey": {
            "cognitive_load": c.cognitive_load_score,
            "perceived_confusion": c.perceived_confusion_score,
            "trust_in_advice": c.trust_in_advice_score,
            "confidence": c.confidence_score,
            "ownership": c.ownership_score,
            "perceived_disagreement": c.perceived_disagreement_score,
            "perceived_breadth": c.perceived_breadth_score,
        },
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "ended_at": c.ended_at.isoformat() if c.ended_at else None,
    }


@router.post("/tts")
async def text_to_speech(request: dict):
    """Convert text to speech audio. Returns MP3 bytes."""
    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    audio_bytes = await tts_service.synthesize(text)
    if not audio_bytes:
        raise HTTPException(status_code=502, detail="TTS service unavailable")
    return Response(content=audio_bytes, media_type="audio/mpeg")


# --- Helpers ---


async def _get_conversation(
    conversation_id: uuid.UUID,
    participant_id: uuid.UUID,
    db: AsyncSession,
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.participant_id != participant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return conversation
