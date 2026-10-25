import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY

from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types
from src.tools import search_expense_policy, check_approval, read_receipt, calculate

course_agent = Agent(
    name="CourseAgent",
    model=settings.LLM_MODEL,
    instruction=(
        "You are the Course Specialist Agent. Audit course, certification, and training expenses.\n"
        "1. Call search_expense_policy(category='COURSE') to get spending limits and approval criteria.\n"
        "2. Check if the claimed amount exceeds the ₹10,000 threshold:\n"
        "   - If amount > 10000: Manager approval is MANDATORY. You MUST call check_approval(employee_id=..., category='COURSE', amount=...).\n"
        "   - If amount <= 10000: Manager approval is NOT required. Do NOT call check_approval.\n"
        "3. Call read_receipt(expense_id=..., receipt_path=...) to validate receipt amount.\n"
        "4. Conclude with audit classification: COMPLIANT, POLICY_EXCEPTION, MISSING_APPROVAL, or RECEIPT_MISMATCH."
    ),
    tools=[search_expense_policy, check_approval, read_receipt, calculate]
)

wfh_agent = Agent(
    name="WfhSetupAgent",
    model=settings.LLM_MODEL,
    instruction=(
        "You are the WFH Setup Specialist Agent. Audit work-from-home equipment claims (monitors, keyboards, mice, webcams, headphones, etc.).\n"
        "1. Call search_expense_policy(category='WFH_SETUP') to retrieve equipment reimbursement limits.\n"
        "2. IMPORTANT: Manager pre-approval is NOT required for standard WFH equipment. Skip manager approval. Do NOT call check_approval.\n"
        "3. Call read_receipt(expense_id=..., receipt_path=...) to validate receipt.\n"
        "4. If amount exceeds the policy limit for the specific item, call calculate to verify the excess variance.\n"
        "5. Conclude with final audit classification."
    ),
    tools=[search_expense_policy, read_receipt, calculate]
)

root_agent = Agent(
    name="ExpenseRootOrchestrator",
    model=settings.LLM_MODEL,
    instruction=(
        "You are the Root Expense Audit Orchestrator. When an expense claim is received, "
        "inspect its description/category and transfer to:\n"
        "- CourseAgent for courses or certifications\n"
        "- WfhSetupAgent for work-from-home home office equipment"
    ),
    sub_agents=[course_agent, wfh_agent]
)

runner = InMemoryRunner(agent=root_agent)
session_id = f"test_{uuid.uuid4().hex[:6]}"
session = runner.session_service.create_session_sync(app_name=runner.app_name, user_id="test_user", session_id=session_id)

user_msg = "Audit my ₹12,000 Dell 24-inch Monitor for home office for employee EMP002, expense_id EXP-112, receipt_path receipts/exp_112.png"
msg = types.Content(parts=[types.Part.from_text(text=user_msg)], role="user")

recorded_steps = []
turn_idx = 1
llm_calls_count = 0

for event in runner.run(user_id="test_user", session_id=session_id, new_message=msg):
    author = event.author
    if event.content and event.content.parts:
        for p in event.content.parts:
            if getattr(p, "function_call", None):
                llm_calls_count += 1
                fc = p.function_call
                recorded_steps.append({
                    "step": turn_idx,
                    "author": author,
                    "action": fc.name,
                    "args": dict(fc.args or {})
                })
                turn_idx += 1
            elif getattr(p, "text", None):
                llm_calls_count += 1
                recorded_steps.append({
                    "step": turn_idx,
                    "author": author,
                    "action": "final_response",
                    "text": p.text[:80]
                })
                turn_idx += 1

print(f"Total LLM Inference Turns observed for WFH: {llm_calls_count}")
for s in recorded_steps:
    print(f"Step {s['step']}: [{s['author']}] action={s['action']} args={s.get('args', s.get('text'))}")
