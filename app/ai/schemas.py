from typing import Literal
from pydantic import BaseModel, Field

ActionType = Literal["enroll_in_sequence","stop_sequence","send_personalized_email","show_in_app_message","create_sales_task","notify_support","invite_to_webinar","request_feedback","recommend_next_product","pause_communication","take_no_action"]

class PlannerDecision(BaseModel):
    action_type: ActionType
    reason_codes: list[str] = Field(max_length=5)
    explanation: str = Field(min_length=1,max_length=500)
    confidence: float = Field(ge=0,le=1)

class AgentRun(BaseModel):
    output: dict
    provider: str
    model: str
    fallback_used: bool
    error: str | None = None
