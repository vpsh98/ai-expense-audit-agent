"""Tests verifying Google ADK Root Agent Orchestration and Specialist Agents."""
import pytest
from google.adk import Agent
from src.agent import (
    ADKExpenseOrchestrator,
    CourseAgent,
    WfhSetupAgent,
    TravelAgent,
    SoftwareLicenseAgent,
    ExpenseAuditAgent,
    LLMClient,
    default_registry,
)
from src.models import AuditClassification, AuditSummary, AgentStep, ToolResult
from src.ui.components import format_agent_step_title


def test_adk_orchestrator_initialization_and_hierarchy():
    """Verify ADK root agent and sub-agents hierarchy are correctly configured."""
    orchestrator = ADKExpenseOrchestrator(tool_registry=default_registry)

    # 1. Verify root ADK agent
    root = orchestrator.adk_root_agent
    assert isinstance(root, Agent)
    assert root.name == "ExpenseRootOrchestrator"
    assert len(root.sub_agents) == 4

    sub_agent_names = [sa.name for sa in root.sub_agents]
    assert "CourseAgent" in sub_agent_names
    assert "WfhSetupAgent" in sub_agent_names
    assert "TravelAgent" in sub_agent_names
    assert "SoftwareLicenseAgent" in sub_agent_names


def test_adk_specialist_agents_tools_reused():
    """Verify specialist agents reuse existing domain tools."""
    orchestrator = ADKExpenseOrchestrator(tool_registry=default_registry)

    # CourseAgent tools
    course_tool_names = [t.__name__ for t in orchestrator.course_agent.adk_agent.tools]
    assert "search_expense_policy" in course_tool_names
    assert "check_approval" in course_tool_names
    assert "read_receipt" in course_tool_names

    # WfhSetupAgent tools
    wfh_tool_names = [t.__name__ for t in orchestrator.wfh_agent.adk_agent.tools]
    assert "search_expense_policy" in wfh_tool_names
    assert "calculate" in wfh_tool_names
    assert "read_receipt" in wfh_tool_names

    # TravelAgent tools
    travel_tool_names = [t.__name__ for t in orchestrator.travel_agent.adk_agent.tools]
    assert "search_expense_policy" in travel_tool_names
    assert "check_approval" in travel_tool_names
    assert "read_receipt" in travel_tool_names
    assert "calculate" in travel_tool_names

    # SoftwareLicenseAgent tools
    software_tool_names = [t.__name__ for t in orchestrator.software_agent.adk_agent.tools]
    assert "search_expense_policy" in software_tool_names
    assert "check_approval" in software_tool_names
    assert "read_receipt" in software_tool_names


def test_adk_course_orchestration_flow():
    """Verify observable orchestration for COURSE: Root -> CourseAgent -> Policy -> Approval -> Receipt."""
    agent = ExpenseAuditAgent(llm_client=LLMClient(mock_mode=True), tool_registry=default_registry)
    summary = agent.run_audit("₹18,000 AWS certification course")

    assert isinstance(summary, AuditSummary)
    assert len(summary.findings) == 1
    finding = summary.findings[0]

    # Verify observable orchestration path
    assert "✓ Root Agent received request" in finding.routing_path
    assert "🔀 Routed to CourseAgent" in finding.routing_path
    assert "✓ Category: COURSE" in finding.routing_path
    assert "→ Course Policy" in finding.routing_path
    assert "→ Approval required" in finding.routing_path
    assert "→ Checking Approval" in finding.routing_path
    assert "→ Receipt validation" in finding.routing_path
    assert "✓ Complete" in finding.routing_path

    # Verify trace tools
    trace = agent.get_execution_trace()
    tool_names = [s.action for s in trace if s.action]
    assert "search_expense_policy" in tool_names
    assert "check_approval" in tool_names
    assert "read_receipt" in tool_names


def test_adk_wfh_orchestration_flow():
    """Verify observable orchestration for WFH_SETUP: Root -> WfhSetupAgent -> WFH Policy -> Monitor limit -> Receipt."""
    agent = ExpenseAuditAgent(llm_client=LLMClient(mock_mode=True), tool_registry=default_registry)
    summary = agent.run_audit("₹18,500 monitor for home office")

    assert isinstance(summary, AuditSummary)
    assert len(summary.findings) == 1
    finding = summary.findings[0]

    # Verify observable orchestration path
    assert "✓ Root Agent received request" in finding.routing_path
    assert "🔀 Routed to WfhSetupAgent" in finding.routing_path
    assert "✓ Category: WFH_SETUP" in finding.routing_path
    assert "→ WFH Policy" in finding.routing_path
    assert "→ Monitor limit check" in finding.routing_path
    assert "⊘ Approval not required" in finding.routing_path
    assert "→ Receipt validation" in finding.routing_path
    assert "✓ Complete" in finding.routing_path

    # Over-limit item invokes calculate tool
    trace = agent.get_execution_trace()
    tool_names = [s.action for s in trace if s.action]
    assert "search_expense_policy" in tool_names
    assert "calculate" in tool_names
    assert "read_receipt" in tool_names
    assert "check_approval" not in tool_names
    assert finding.calculated_variance == 3500.0


def test_adk_multi_item_report_orchestration():
    """Verify multi-item report triggers root agent triage and specialist delegation across line items."""
    agent = ExpenseAuditAgent(llm_client=LLMClient(mock_mode=True), tool_registry=default_registry)
    summary = agent.run_audit("Audit Rajesh Kumar's September expenses")

    assert isinstance(summary, AuditSummary)
    assert summary.total_items_audited > 0

    trace = agent.get_execution_trace()
    tool_names = [s.action for s in trace if s.action]
    assert "get_employee_details" in tool_names
    assert "read_expense_report" in tool_names
    assert "search_expense_policy" in tool_names
    assert "calculate" in tool_names
    assert "check_approval" in tool_names


def test_ui_activity_feed_adk_step_title():
    """Verify UI activity feed renders ADK orchestration step titles."""
    step_root = AgentStep(
        step_number=1,
        thought="✓ Root Agent received expense audit request",
        action="adk_root",
        action_input={"query": "test"},
        observation="OK",
    )
    title_root = format_agent_step_title(step_root)
    assert "ADK Root Orchestrator" in title_root

    step_delegate = AgentStep(
        step_number=2,
        thought="Dispatching to specialist",
        action="route_to_specialist",
        action_input={"specialist": "CourseAgent"},
        observation="Routed",
    )
    title_delegate = format_agent_step_title(step_delegate)
    assert "ADK Dispatch" in title_delegate
    assert "CourseAgent" in title_delegate


def test_adk_root_agent_and_specialists_have_gemini_model():
    """Verify Root Agent and Specialists are backed by the configured Gemini model."""
    orchestrator = ADKExpenseOrchestrator(tool_registry=default_registry)
    assert orchestrator.adk_root_agent.model is not None
    assert "gemini" in orchestrator.adk_root_agent.model.lower()
    for sub in orchestrator.adk_root_agent.sub_agents:
        assert sub.model is not None
        assert "gemini" in sub.model.lower()


def test_ui_activity_feed_transfer_to_agent_title():
    """Verify UI activity feed renders transfer_to_agent step titles."""
    step = AgentStep(
        step_number=1,
        thought="Root Orchestrator delegated claim to specialist: CourseAgent",
        action="transfer_to_agent",
        action_input={"agent_name": "CourseAgent"},
        observation=ToolResult(tool_name="transfer_to_agent", success=True, result={"transferred_to": "CourseAgent"})
    )
    title = format_agent_step_title(step)
    assert "Root Agent → CourseAgent" in title
    assert "ADK Sub-Agent Transfer" in title

