import pytest
from src.agent import ToolRegistry, default_registry
from src.tools import BaseTool, calculator_tool
from src.models import ToolResult

def test_tool_registry_registration():
    registry = ToolRegistry()
    assert len(registry) == 0

    # Register individual tool
    registry.register(calculator_tool)
    assert len(registry) == 1
    assert "calculate" in registry
    assert registry.get("calculate") == calculator_tool


def test_tool_registry_defaults_and_demo_validation():
    registry = ToolRegistry()
    registry.register_defaults()

    # Demo Validation: Verify all core tools are registered and schemas generated correctly
    assert len(registry) == 6
    tools_list = registry.list_tools()
    assert "calculate" in tools_list
    assert "get_employee_details" in tools_list
    assert "read_expense_report" in tools_list
    assert "search_expense_policy" in tools_list
    assert "check_approval" in tools_list
    assert "read_receipt" in tools_list

    # Verify standard / Gemini schema format
    schemas_std = registry.get_schemas("standard")
    assert len(schemas_std) == 6
    for schema in schemas_std:
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
        assert isinstance(schema["parameters"], dict)

    # Verify OpenAI schema format
    schemas_openai = registry.get_schemas("openai")
    assert len(schemas_openai) == 6
    for schema in schemas_openai:
        assert schema["type"] == "function"
        assert "function" in schema
        fn = schema["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn


def test_tool_registry_execution():
    registry = ToolRegistry()
    registry.register_defaults()

    # Dispatch calculate tool
    res_calc = registry.execute("calculate", {"operation": "subtract", "a": 9500.0, "b": 8000.0})
    assert isinstance(res_calc, ToolResult)
    assert res_calc.success is True
    assert res_calc.result["value"] == 1500.0

    # Dispatch search_expense_policy tool
    res_policy = registry.execute("search_expense_policy", {"category": "Hotel"})
    assert isinstance(res_policy, ToolResult)
    assert res_policy.success is True
    assert res_policy.result["limit_amount"] == 8000.0

    # Dispatch read_receipt tool
    res_rcp = registry.execute("read_receipt", {"expense_id": "EXP-101"})
    assert isinstance(res_rcp, ToolResult)
    assert res_rcp.success is True
    assert res_rcp.result["found"] is True

    # Dispatch nonexistent tool
    res_missing = registry.execute("nonexistent_tool", {})
    assert isinstance(res_missing, ToolResult)
    assert res_missing.success is False
    assert "not registered" in res_missing.error.lower()
