import os
import sys
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
    model="gemini-3.5-flash-lite",
    instruction=(
        "You are the Course Specialist Agent. Audit course and certification expenses.\n"
        "1. Call search_expense_policy(category='COURSE') to get policy limits.\n"
        "2. If amount > 10000, call check_approval(employee_id=..., category='COURSE', amount=...).\n"
        "   If amount <= 10000, skip approval.\n"
        "3. Call read_receipt(expense_id=..., receipt_path=...) to validate receipt.\n"
        "State your final audit decision clearly."
    ),
    tools=[search_expense_policy, check_approval, read_receipt]
)

wfh_agent = Agent(
    name="WfhSetupAgent",
    model="gemini-3.5-flash-lite",
    instruction=(
        "You are the WFH Setup Specialist Agent. Audit work-from-home equipment claims (monitors, keyboards, mice, webcams, headphones, etc.).\n"
        "1. Call search_expense_policy(category='WFH_SETUP') to retrieve equipment reimbursement limits.\n"
        "2. IMPORTANT: Manager pre-approval is NOT required for WFH equipment. Skip manager approval.\n"
        "3. Call read_receipt(expense_id=..., receipt_path=...) to validate receipt.\n"
        "4. If amount exceeds the policy limit for the specific item, call calculate to verify the excess variance.\n"
        "State your final audit decision clearly."
    ),
    tools=[search_expense_policy, read_receipt, calculate]
)

root_agent = Agent(
    name="ExpenseRootOrchestrator",
    model="gemini-3.5-flash-lite",
    instruction=(
        "You are the Root Expense Audit Orchestrator. When an expense claim is received, "
        "inspect its nature and transfer to the appropriate specialist agent:\n"
        "- Transfer to CourseAgent for courses, certifications, workshops, or education.\n"
        "- Transfer to WfhSetupAgent for work-from-home home office equipment (monitors, keyboards, webcams, headphones, etc.)."
    ),
    sub_agents=[course_agent, wfh_agent]
)

runner = InMemoryRunner(agent=root_agent)
session = runner.session_service.create_session_sync(app_name=runner.app_name, user_id="test_user", session_id="test_sess_2")
msg = types.Content(parts=[types.Part.from_text(text="Audit my ₹12,000 Dell 24-inch Monitor for home office for employee EMP002, expense_id EXP-112, receipt_path receipts/exp_112.png")], role="user")

print("--- Starting WFH ADK Execution ---")
for event in runner.run(user_id="test_user", session_id="test_sess_2", new_message=msg):
    author = event.author
    if event.content and event.content.parts:
        for p in event.content.parts:
            if getattr(p, "function_call", None):
                print(f"[{author}] Tool Call: {p.function_call.name}({p.function_call.args})")
            elif getattr(p, "function_response", None):
                print(f"[{author}] Tool Response: {p.function_response.name}")
            elif getattr(p, "text", None):
                print(f"[{author}] Text: {p.text[:120]}...")
    if event.actions and event.actions.transfer_to_agent:
        print(f"[{author}] Delegated to: {event.actions.transfer_to_agent}")
print("--- WFH ADK Execution Completed ---")
