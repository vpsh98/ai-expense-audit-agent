import os
from src.config import settings
os.environ['GEMINI_API_KEY'] = settings.GEMINI_API_KEY
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from src.tools import search_expense_policy, check_approval, read_receipt, calculate

course_agent = Agent(
    name='CourseAgent',
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
    name='WfhSetupAgent',
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
    name='TravelAgent',
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
    name='SoftwareLicenseAgent',
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
    name='ExpenseRootOrchestrator',
    model=settings.LLM_MODEL,
    instruction=(
        "You are the Root Expense Audit Orchestrator. When an expense claim is received, "
        "inspect its description/category and transfer to the appropriate specialist agent:\n"
        "- CourseAgent for education, courses, or certifications\n"
        "- WfhSetupAgent for work-from-home home office equipment\n"
        "- TravelAgent for travel, flight, hotel, taxi, or meals\n"
        "- SoftwareLicenseAgent for software licenses, subscriptions, or IDE tools\n"
        "Delegate by transferring to the specialist agent."
    ),
    sub_agents=[course_agent, wfh_agent, travel_agent, software_agent]
)

print('Root and specialist agents initialized successfully with model:', settings.LLM_MODEL)
print('Root sub_agents:', [sa.name for sa in root_agent.sub_agents])
