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

travel_agent = Agent(
    name="TravelAgent",
    model=settings.LLM_MODEL,
    instruction=(
        "You are the Travel Specialist Agent. Audit travel expenses (hotel, flight, taxi, meals).\n"
        "1. Call search_expense_policy(category=...) to get limits.\n"
        "2. If amount exceeds limits, check approval if needed.\n"
        "3. Call read_receipt(expense_id=..., receipt_path=...) to validate receipt.\n"
        "4. Conclude with final audit classification."
    ),
    tools=[search_expense_policy, check_approval, read_receipt, calculate]
)

software_agent = Agent(
    name="SoftwareLicenseAgent",
    model=settings.LLM_MODEL,
    instruction=(
        "You are the Software License Specialist Agent. Audit software licenses and SaaS tools.\n"
        "1. Call search_expense_policy(category='SOFTWARE_LICENSE') to get limits.\n"
        "2. If amount > 5000, call check_approval.\n"
        "3. Call read_receipt(expense_id=..., receipt_path=...) to validate receipt.\n"
        "4. Conclude with final audit classification."
    ),
    tools=[search_expense_policy, check_approval, read_receipt, calculate]
)

root_agent = Agent(
    name="ExpenseRootOrchestrator",
    model=settings.LLM_MODEL,
    instruction=(
        "You are the Root Expense Audit Orchestrator. When an expense claim is received, "
        "inspect its description/category and transfer to the appropriate specialist agent:\n"
        "- CourseAgent for education, courses, or certifications\n"
        "- WfhSetupAgent for work-from-home home office equipment\n"
        "- TravelAgent for travel, flight, hotel, taxi, or meals\n"
        "- SoftwareLicenseAgent for software licenses, subscriptions, or IDE tools\n"
        "Transfer immediately using the transfer_to_agent function."
    ),
    sub_agents=[course_agent, wfh_agent, travel_agent, software_agent]
)

runner = InMemoryRunner(agent=root_agent)

def run_query(query_text):
    print("=" * 60)
    print(f"RUNNING QUERY: '{query_text}'")
    print("=" * 60)
    session_id = f"test_{uuid.uuid4().hex[:6]}"
    runner.session_service.create_session_sync(app_name=runner.app_name, user_id="test_user", session_id=session_id)
    msg = types.Content(parts=[types.Part.from_text(text=query_text)], role="user")
    
    step_num = 1
    llm_turns = 0
    tools_called = []
    
    for event in runner.run(user_id="test_user", session_id=session_id, new_message=msg):
        author = event.author
        if event.actions and event.actions.transfer_to_agent:
            print(f"[{author}] -> Transfer to agent: {event.actions.transfer_to_agent}")
        if event.content and event.content.parts:
            for p in event.content.parts:
                if getattr(p, "function_call", None):
                    llm_turns += 1
                    fc = p.function_call
                    tools_called.append(fc.name)
                    print(f"Step {step_num} (LLM turn {llm_turns}): [{author}] Function Call: {fc.name}({dict(fc.args or {})})")
                    step_num += 1
                elif getattr(p, "function_response", None):
                    fr = p.function_response
                    print(f"          [{author}] Function Response: {fr.name} -> {str(fr.response)[:100]}...")
                elif getattr(p, "text", None):
                    llm_turns += 1
                    print(f"Step {step_num} (LLM turn {llm_turns}): [{author}] Text: {p.text.strip()[:150]}...")
                    step_num += 1

    print(f"\nSummary for '{query_text}':")
    print(f"- Total LLM inference turns: {llm_turns}")
    print(f"- Tools called: {tools_called}\n")

run_query("Audit my ₹18,000 AWS certification course for employee EMP002, expense_id EXP-110, receipt_path receipts/exp_110.png")
run_query("Audit my ₹12,000 monitor purchase for home office for employee EMP002, expense_id EXP-112, receipt_path receipts/exp_112.png")
