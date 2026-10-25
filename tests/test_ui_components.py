import pytest
from src.models import AgentStep, ToolResult
from src.ui.components import format_agent_step_title

def test_format_agent_step_title_employee_details():
    step = AgentStep(
        step_number=1,
        thought="Identify Rajesh Kumar",
        action="get_employee_details",
        action_input={"employee_name": "Rajesh Kumar"},
        observation=ToolResult(tool_name="get_employee_details", success=True)
    )
    title = format_agent_step_title(step)
    assert "Looking up profile" in title
    assert "Rajesh Kumar" in title


def test_format_agent_step_title_expense_report():
    step = AgentStep(
        step_number=2,
        thought="Read expenses for EMP001",
        action="read_expense_report",
        action_input={"employee_id": "EMP001", "period": "2026-09"},
        observation=ToolResult(tool_name="read_expense_report", success=True)
    )
    title = format_agent_step_title(step)
    assert "Fetching expense line items" in title
    assert "EMP001" in title


def test_format_agent_step_title_policy_search():
    step = AgentStep(
        step_number=3,
        thought="Search policy for Hotel",
        action="search_expense_policy",
        action_input={"category": "Hotel"},
        observation=ToolResult(tool_name="search_expense_policy", success=True)
    )
    title = format_agent_step_title(step)
    assert "Querying spending policy" in title
    assert "Hotel" in title


def test_format_agent_step_title_calculate():
    step = AgentStep(
        step_number=4,
        thought="Calculate variance",
        action="calculate",
        action_input={"operation": "subtract", "a": 9500, "b": 8000},
        observation=ToolResult(tool_name="calculate", success=True, result={"value": 1500.0})
    )
    title = format_agent_step_title(step)
    assert "Calculating" in title
    assert "9500 vs 8000" in title
    assert "1,500.00" in title


def test_format_agent_step_title_check_approval():
    step = AgentStep(
        step_number=5,
        thought="Check pre-approval",
        action="check_approval",
        action_input={"category": "Hotel", "amount": 12000.0},
        observation=ToolResult(tool_name="check_approval", success=True)
    )
    title = format_agent_step_title(step)
    assert "Verifying manager pre-approval" in title
    assert "Hotel" in title


def test_format_agent_step_title_read_receipt():
    step = AgentStep(
        step_number=6,
        thought="Inspect receipt",
        action="read_receipt",
        action_input={"expense_id": "EXP-101"},
        observation=ToolResult(tool_name="read_receipt", success=True)
    )
    title = format_agent_step_title(step)
    assert "Inspecting digital receipt" in title
    assert "EXP-101" in title
