from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_participant
from app.models.participant import Participant
from app.models.survey import Survey, SurveyType
from app.schemas.survey import (
    SURVEY_CONFIGS,
    PendingSurvey,
    SurveyConfig,
    SurveyResponse,
    SurveySubmitRequest,
)

router = APIRouter(prefix="/api/v1/surveys", tags=["surveys"])


def _compute_week(participant: Participant) -> int:
    created = participant.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - created).days
    return max(1, (days // 7) + 1)


@router.get("/config/{survey_type}", response_model=SurveyConfig)
async def get_survey_config(survey_type: str):
    """Get the question config for a survey type."""
    config = SURVEY_CONFIGS.get(survey_type)
    if not config:
        raise HTTPException(
            status_code=404, detail=f"Unknown survey type: {survey_type}"
        )
    return config


@router.get("/pending", response_model=list[PendingSurvey])
async def get_pending_surveys(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Get surveys the participant needs to complete."""
    # Get all completed surveys for this participant
    result = await db.execute(
        select(Survey).where(Survey.participant_id == participant.id)
    )
    completed = {(s.type.value, s.week_number) for s in result.scalars().all()}
    week = _compute_week(participant)

    pending: list[PendingSurvey] = []

    # Baseline: if not completed
    if ("baseline", None) not in completed and ("baseline", 0) not in completed:
        cfg = SURVEY_CONFIGS["baseline"]
        pending.append(
            PendingSurvey(
                survey_type="baseline", title=cfg.title, description=cfg.description
            )
        )

    # Weekly pulse: for the current week if not completed
    if ("weekly_pulse", week) not in completed:
        cfg = SURVEY_CONFIGS["weekly_pulse"]
        pending.append(
            PendingSurvey(
                survey_type="weekly_pulse",
                title=cfg.title,
                description=cfg.description,
                week_number=week,
            )
        )

    # Midpoint: after week 3
    if (
        week >= 3
        and ("midpoint", None) not in completed
        and ("midpoint", 0) not in completed
    ):
        cfg = SURVEY_CONFIGS["midpoint"]
        pending.append(
            PendingSurvey(
                survey_type="midpoint", title=cfg.title, description=cfg.description
            )
        )

    # Endline: after week 6
    if (
        week >= 6
        and ("endline", None) not in completed
        and ("endline", 0) not in completed
    ):
        cfg = SURVEY_CONFIGS["endline"]
        pending.append(
            PendingSurvey(
                survey_type="endline", title=cfg.title, description=cfg.description
            )
        )

    return pending


@router.post("", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED)
async def submit_survey(
    request: SurveySubmitRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Submit a completed survey."""
    if request.survey_type not in SURVEY_CONFIGS:
        raise HTTPException(
            status_code=400, detail=f"Unknown survey type: {request.survey_type}"
        )

    try:
        survey_type_enum = SurveyType(request.survey_type)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid survey type: {request.survey_type}"
        )

    survey = Survey(
        participant_id=participant.id,
        week_number=request.week_number,
        type=survey_type_enum,
        responses=request.responses,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(survey)
    await db.commit()
    await db.refresh(survey)

    return SurveyResponse.model_validate(survey)


@router.get("", response_model=list[SurveyResponse])
async def list_surveys(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """List all completed surveys for the participant."""
    result = await db.execute(
        select(Survey)
        .where(Survey.participant_id == participant.id)
        .order_by(Survey.completed_at.desc())
    )
    return [SurveyResponse.model_validate(s) for s in result.scalars().all()]
