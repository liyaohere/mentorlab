import uuid
from datetime import datetime

from pydantic import BaseModel


class SurveyQuestion(BaseModel):
    id: str
    text: str
    type: str  # "text", "number", "likert", "choice", "multi_choice"
    required: bool = True
    options: list[str] | None = None  # for choice/multi_choice
    min_value: int | None = None      # for likert/number
    max_value: int | None = None
    min_label: str | None = None      # e.g. "Strongly disagree"
    max_label: str | None = None      # e.g. "Strongly agree"


class SurveyConfig(BaseModel):
    type: str  # baseline, weekly_pulse, midpoint, endline
    title: str
    description: str = ""
    questions: list[SurveyQuestion]


class SurveySubmitRequest(BaseModel):
    survey_type: str
    week_number: int | None = None
    responses: dict  # question_id -> answer


class SurveyResponse(BaseModel):
    id: uuid.UUID
    participant_id: uuid.UUID
    week_number: int | None
    type: str
    responses: dict
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PendingSurvey(BaseModel):
    """A survey that needs to be completed."""
    survey_type: str
    title: str
    description: str
    week_number: int | None = None


# --- Default survey configurations ---

WEEKLY_PULSE_SURVEY = SurveyConfig(
    type="weekly_pulse",
    title="Weekly Check-in",
    description="A quick reflection on this week's mentoring conversation.",
    questions=[
        SurveyQuestion(
            id="helpful",
            text="How helpful was this week's conversation with your mentor?",
            type="likert",
            min_value=1, max_value=5,
            min_label="Not helpful at all", max_label="Extremely helpful",
        ),
        SurveyQuestion(
            id="new_ideas",
            text="Did the conversation give you any new ideas for your business?",
            type="choice",
            options=["Yes, several new ideas", "Yes, one or two", "Not really", "No"],
        ),
        SurveyQuestion(
            id="action",
            text="What is one thing you plan to do differently this week based on the conversation?",
            type="text",
            required=False,
        ),
    ],
)

BASELINE_SURVEY = SurveyConfig(
    type="baseline",
    title="Getting Started Survey",
    description="Help us understand your business and background. This takes about 5 minutes.",
    questions=[
        SurveyQuestion(id="revenue_monthly", text="What is your approximate monthly revenue (UGX)?", type="number"),
        SurveyQuestion(id="team_size", text="How many people work in your business (including you)?", type="number"),
        SurveyQuestion(id="years_operating", text="How many years has your business been operating?", type="number"),
        SurveyQuestion(
            id="biggest_challenge",
            text="What is the biggest challenge your business faces right now?",
            type="choice",
            options=["Finding customers", "Managing money/cash flow", "Competition", "Getting supplies", "Finding skilled workers", "Other"],
        ),
        SurveyQuestion(
            id="business_confidence",
            text="How confident are you that your business will grow in the next 6 months?",
            type="likert", min_value=1, max_value=5,
            min_label="Not confident at all", max_label="Very confident",
        ),
        SurveyQuestion(
            id="mentor_experience",
            text="Have you ever had a business mentor before?",
            type="choice",
            options=["Yes", "No"],
        ),
    ],
)

MIDPOINT_SURVEY = SurveyConfig(
    type="midpoint",
    title="Midpoint Check-in",
    description="You're halfway through the program! We'd love your feedback.",
    questions=[
        SurveyQuestion(
            id="overall_satisfaction",
            text="Overall, how satisfied are you with the mentoring program so far?",
            type="likert", min_value=1, max_value=5,
            min_label="Very dissatisfied", max_label="Very satisfied",
        ),
        SurveyQuestion(
            id="changed_strategy",
            text="Have you made any changes to your business strategy based on conversations with your mentor?",
            type="choice",
            options=["Yes, major changes", "Yes, small changes", "No, but I'm considering it", "No"],
        ),
        SurveyQuestion(id="feedback", text="What could we improve about the program?", type="text", required=False),
    ],
)

ENDLINE_SURVEY = SurveyConfig(
    type="endline",
    title="Final Survey",
    description="Thank you for participating! Please complete this final survey.",
    questions=[
        SurveyQuestion(id="revenue_monthly", text="What is your approximate monthly revenue now (UGX)?", type="number"),
        SurveyQuestion(id="team_size", text="How many people work in your business now?", type="number"),
        SurveyQuestion(
            id="business_confidence",
            text="How confident are you that your business will grow in the next 6 months?",
            type="likert", min_value=1, max_value=5,
            min_label="Not confident at all", max_label="Very confident",
        ),
        SurveyQuestion(
            id="mentor_value",
            text="How valuable was the AI mentor to your business?",
            type="likert", min_value=1, max_value=5,
            min_label="Not valuable", max_label="Extremely valuable",
        ),
        SurveyQuestion(
            id="would_recommend",
            text="Would you recommend this program to a fellow entrepreneur?",
            type="choice",
            options=["Definitely yes", "Probably yes", "Not sure", "Probably no", "Definitely no"],
        ),
        SurveyQuestion(id="most_helpful", text="What was the most helpful thing about your mentor?", type="text", required=False),
    ],
)

SURVEY_CONFIGS: dict[str, SurveyConfig] = {
    "baseline": BASELINE_SURVEY,
    "weekly_pulse": WEEKLY_PULSE_SURVEY,
    "midpoint": MIDPOINT_SURVEY,
    "endline": ENDLINE_SURVEY,
}
