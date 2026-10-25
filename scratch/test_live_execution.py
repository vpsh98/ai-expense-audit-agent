import os
import sys
import uuid
import re
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
from src.agent.specialists import CourseAgent, WfhSetupAgent, TravelAgent, SoftwareLicenseAgent
from src.models import AgentStep, ToolResult, AuditSummary, AuditFinding, AuditClassification, RiskLevel

def build_test_orchestrator():
    course_agent = CourseAgent()
    wfh_agent = WfhSetupAgent()
    travel_agent = TravelAgent()
    software_agent = SoftwareLicenseAgent()

    root_agent = Agent(
        name="ExpenseRootOrchestrator",
        model=settings.LLM_MODEL,
        description="Root agent orchestrating expense triage and delegation to specialist agents.",
        instruction=(
            "You are the Root Expense Audit Orchestrator. When an expense claim is received, "
            "inspect its description and category, and transfer immediately to the appropriate specialist agent:\n"
            "- CourseAgent for education, training, courses, or certifications\n"
            "- WfhSetupAgent for work-from-home home office equipment (monitors, keyboards, mice, etc.)\n"
            "- TravelAgent for travel, flight, hotel, taxi, or meals\n"
            "- SoftwareLicenseAgent for software licenses, subscriptions, or IDE tools\n"
            "Use the transfer_to_agent function to delegate."
        ),
        sub_agents=[
            course_agent.adk_agent,
            wfh_agent.adk_agent,
            travel_agent.adk_agent,
            software_agent.adk_agent,
        ],
    )
    return root_agent

root_agent = build_test_orchestrator()
runner = InMemoryRunner(agent=root_agent)

def execute_adk(user_request, exp_info):
    session_id = f"test_{uuid.uuid4().hex[:6]}"
    runner.session_service.create_session_sync(app_name=runner.app_name, user_id="test_user", session_id=session_id)
    
    prompt = (
        f"Audit this expense claim: {user_request}\n"
        f"Expense ID: {exp_info['expense_id']}, Employee ID: {exp_info['employee_id']}, "
        f"Category: {exp_info['category']}, Amount: ₹{exp_info['amount']}, "
        f"Receipt: {exp_info['receipt_path']}"
    )
    msg = types.Content(parts=[types.Part.from_text(text=prompt)], role="user")
    
    steps = []
    turn_idx = 1
    llm_turns = 0
    tools_called = []
    pending_tool_calls = {}

    for event in runner.run(user_id="test_user", session_id=session_id, new_message=msg):
        author = event.author or "Agent"
        if event.actions and event.actions.transfer_to_agent:
            target = event.actions.transfer_to_agent
            steps.append(AgentStep(
                step_number=turn_idx,
                thought=f"Root Orchestrator transferred claim to specialist: {target}",
                action="transfer_to_agent",
                action_input={"agent_name": target},
                observation=ToolResult(tool_name="transfer_to_agent", success=True, result={"transferred_to": target})
            ))
            turn_idx += 1

        if event.content and event.content.parts:
            for p in event.content.parts:
                if getattr(p, "function_call", None):
                    llm_turns += 1
                    fc = p.function_call
                    pending_tool_calls[fc.name] = (author, dict(fc.args or {}))
                    tools_called.append(fc.name)
                elif getattr(p, "function_response", None):
                    fr = p.function_response
                    author_name, args = pending_tool_calls.pop(fr.name, (author, {}))
                    res = fr.response
                    tool_obs = res.get("result") if isinstance(res, dict) and "result" in res else res
                    if not isinstance(tool_obs, ToolResult):
                        tool_obs = ToolResult(tool_name=fr.name, success=True, result=tool_obs)
                    steps.append(AgentStep(
                        step_number=turn_idx,
                        thought=f"[{author_name}] Executed tool '{fr.name}'",
                        action=fr.name,
                        action_input=args,
                        observation=tool_obs
                    ))
                    turn_idx += 1
                elif getattr(p, "text", None):
                    llm_turns += 1
                    txt = p.text.strip()
                    if txt:
                        steps.append(AgentStep(
                            step_number=turn_idx,
                            thought=f"[{author}] Synthesized audit conclusion",
                            action=None,
                            action_input=None,
                            observation=txt
                        ))
                        turn_idx += 1

    print(f"\nResults for '{user_request}':")
    print(f"Total LLM Turns: {llm_turns}")
    print(f"Recorded AgentSteps: {len(steps)}")
    for s in steps:
        print(f"  Step {s.step_number}: action={s.action} thought={s.thought}")
    return steps

# 1. Course test
course_info = {"expense_id": "EXP-110", "employee_id": "EMP002", "category": "COURSE", "amount": 18000, "receipt_path": "receipts/exp_110.png"}
execute_adk("Audit my ₹18,000 AWS certification course", course_info)

# 2. WFH test
wfh_info = {"expense_id": "EXP-112", "employee_id": "EMP002", "category": "WFH_SETUP", "amount": 12000, "receipt_path": "receipts/exp_112.png"}
execute_adk("Audit my ₹12,000 monitor purchase for home office", wfh_info)
