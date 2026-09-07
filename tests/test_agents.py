from app.ai.agents import draft_with_agent, plan_with_agent
from app.ai.schemas import PlannerDecision
from app.models import GrowthAction
from app.schemas import OutreachDraft

class StubProvider:
    model="stub"
    def __init__(self,result): self.result=result
    def structured(self,system,prompt,schema): return self.result

def test_planner_accepts_only_allowed_action():
    ok=plan_with_agent({"segment":"lead"},["take_no_action"],StubProvider(PlannerDecision(action_type="take_no_action",reason_codes=["SAFE"],explanation="No contact.",confidence=.9)))
    assert ok.provider=="ollama" and not ok.fallback_used

def test_planner_rejects_action_outside_allowlist():
    bad=plan_with_agent({},["take_no_action"],StubProvider(PlannerDecision(action_type="invite_to_webinar",reason_codes=["BAD"],explanation="Try.",confidence=.5)))
    assert bad.fallback_used and bad.output["action_type"]=="take_no_action"

def test_outreach_rejects_ungrounded_fact():
    action=GrowthAction(action_id="a",user_id="u",action_type="send_personalized_email",status="pending",reason_codes=["COURSE_COMPLETED"],evidence_event_ids=[],context={},idempotency_key="k",requires_approval=True,state_version="v")
    generated=OutreachDraft(subject="Hi",body="Claim",cta="open_course",facts_used=["secret-trait"],confidence=.8,template_version="v1",provider="stub")
    result=draft_with_agent(action,{"purchases":["python"]},StubProvider(generated))
    assert result.fallback_used and result.provider=="deterministic"
