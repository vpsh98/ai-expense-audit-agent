import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.config import settings
os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY

from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types
from src.tools import search_expense_policy, check_approval, read_receipt, calculate

course_agent = Agent(
    name="CourseAgent",
    model=settings.LLM_MODEL,
    instruction="Audit course expenses. Call search_expense_policy, check_approval if > 10k, read_receipt.",
    tools=[search_expense_policy, check_approval, read_receipt]
)

root_agent = Agent(
    name="ExpenseRootOrchestrator",
    model=settings.LLM_MODEL,
    instruction="Transfer to CourseAgent for courses.",
    sub_agents=[course_agent]
)

runner = InMemoryRunner(agent=root_agent)
session_id = f"test_{uuid.uuid4().hex[:6]}"
runner.session_service.create_session_sync(app_name=runner.app_name, user_id="test_user", session_id=session_id)
msg = types.Content(parts=[types.Part.from_text(text="Audit my ₹18,000 AWS certification course for employee EMP002, expense_id EXP-110, receipt_path receipts/exp_110.png")], role="user")

prompt_tokens = 0
candidate_tokens = 0
total_tokens = 0

for ev in runner.run(user_id="test_user", session_id=session_id, new_message=msg):
    if hasattr(ev, "usage_metadata") and ev.usage_metadata:
        um = ev.usage_metadata
        p_cnt = getattr(um, "prompt_token_count", 0) or 0
        c_cnt = getattr(um, "candidates_token_count", 0) or 0
        t_cnt = getattr(um, "total_token_count", 0) or 0
        if t_cnt > 0:
            prompt_tokens += p_cnt
            candidate_tokens += c_cnt
            total_tokens += t_cnt

cost_usd = (prompt_tokens * 0.075 / 1_000_000) + (candidate_tokens * 0.30 / 1_000_000)
cost_inr = cost_usd * 86.5

print(f"Prompt Tokens: {prompt_tokens}")
print(f"Candidate Tokens: {candidate_tokens}")
print(f"Total Tokens: {total_tokens}")
print(f"Estimated Cost USD: ${cost_usd:.6f}")
print(f"Estimated Cost INR: ₹{cost_inr:.4f}")
