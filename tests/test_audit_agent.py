import pytest
from src.agent import ExpenseAuditAgent, LLMClient, default_registry
from src.models import AuditSummary, AuditClassification, AgentStep

def test_audit_agent_rajesh_kumar_demo():
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    summary = agent.run_audit("Audit Rajesh Kumar's September expenses")

    assert isinstance(summary, AuditSummary)
    assert summary.total_items_audited > 0
    assert len(summary.findings) > 0

    # Verify execution trace
    trace = agent.get_execution_trace()
    assert len(trace) > 0

    tool_names = [step.action for step in trace if step.action]
    assert "get_employee_details" in tool_names
    assert "read_expense_report" in tool_names
    assert "search_expense_policy" in tool_names
    assert "calculate" in tool_names
    assert "check_approval" in tool_names

    # Verify findings contain proper classifications
    classifications = [f.classification for f in summary.findings]
    assert AuditClassification.COMPLIANT in classifications
    assert AuditClassification.REQUIRES_REVIEW in classifications or AuditClassification.MISSING_APPROVAL in classifications or AuditClassification.POLICY_EXCEPTION in classifications


def test_audit_agent_branching_policy_exception():
    # Test Vikram Patel audit (Hotel ₹12,000 > ₹8,000 policy, has pre-approval)
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    summary = agent.run_audit("Audit Vikram Patel's expenses")
    assert isinstance(summary, AuditSummary)
    assert summary.total_items_audited > 0

    # Verify check_approval was called for over-limit item
    trace = agent.get_execution_trace()
    tool_names = [step.action for step in trace if step.action]
    assert "check_approval" in tool_names


def test_audit_agent_max_turns_safeguard():
    # Test setting max_turns = 1 stops loop
    llm_client = LLMClient(mock_mode=False) # Non-mock client to test loop limit with dummy text
    llm_client.mock_mode = False
    
    # Mock generator returning perpetual tool calls
    def looping_generator(messages, tools, system_instruction=None, temperature=0.2):
        return {
            "content": None,
            "tool_calls": [{"name": "search_expense_policy", "arguments": {"category": "Hotel"}}]
        }
    
    llm_client._generate_gemini = looping_generator
    
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry, max_turns=3)
    summary = agent.run_audit("Loop test")
    
    trace = agent.get_execution_trace()
    assert len(trace) == 3  # Stopped exactly at max_turns = 3


def test_convenience_audit_wrapper():
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client)

    summary = agent.audit_employee_expenses("EMP001", period="2026-09")
    assert summary.total_items_audited >= 3


def test_audit_different_employees_distinct_results():
    """Verify that auditing different employees produces distinct, correct results."""
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client)

    # Ananya Sharma (EMP002) has 5 expenses: Course, WFH, Software, Taxi
    s_ananya = agent.run_audit("Audit Ananya Sharma's expenses")
    assert s_ananya.total_items_audited == 5
    ananya_items = [f.item_id for f in s_ananya.findings]
    assert "EXP-105" in ananya_items
    assert "EXP-110" in ananya_items
    assert "EXP-112" in ananya_items

    # Vikram Patel (EMP003) has 1 hotel expense
    s_vikram = agent.run_audit("Audit Vikram Patel's expenses")
    assert s_vikram.total_items_audited == 1
    assert s_vikram.findings[0].item_id == "EXP-104"

    # Amit Varma (EMP004) has 1 meals expense
    s_amit = agent.run_audit("Audit Amit Varma's expenses")
    assert s_amit.total_items_audited == 1
    assert s_amit.findings[0].item_id == "EXP-108"

    # Priya Nair (EMP005) has 1 gifts expense
    s_priya = agent.run_audit("Audit Priya Nair's expenses")
    assert s_priya.total_items_audited == 1
    assert s_priya.findings[0].item_id == "EXP-106"

    # Rajesh Kumar (EMP001) has 8 expenses
    s_rajesh = agent.run_audit("Audit Rajesh Kumar's expenses")
    assert s_rajesh.total_items_audited == 8
