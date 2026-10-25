import pytest
from src.tools import BaseTool, CalculatorTool, calculator_tool, calculate
from src.models import ToolResult

def test_calculator_operations():
    # Test addition
    res_add = calculate(operation="add", a=1200.0, b=1800.0)
    assert res_add.success is True
    assert res_add.result["value"] == 3000.0
    assert res_add.formatted_result == "3000.00"

    # Test subtraction (Demo validation requirement)
    res_sub = calculate(operation="subtract", a=9500.0, b=8000.0)
    assert res_sub.success is True
    assert res_sub.result["value"] == 1500.0
    assert res_sub.formatted_result == "1500.00"

    # Test multiplication
    res_mul = calculate(operation="multiply", a=800.0, b=5.0)
    assert res_mul.success is True
    assert res_mul.result["value"] == 4000.0

    # Test division
    res_div = calculate(operation="divide", a=15000.0, b=3.0)
    assert res_div.success is True
    assert res_div.result["value"] == 5000.0

    # Test percentage
    res_pct = calculate(operation="percentage", a=4500.0, b=3000.0)
    assert res_pct.success is True
    assert res_pct.result["value"] == 50.0
    assert res_pct.formatted_result == "50.00"


def test_calculator_rounding():
    # 10 / 3 = 3.33333... -> rounded to 3.33
    res = calculate(operation="divide", a=10.0, b=3.0)
    assert res.success is True
    assert res.result["value"] == 3.33
    assert res.formatted_result == "3.33"


def test_division_by_zero_safeguard():
    # Division by zero should fail gracefully with ToolResult success=False
    res_div = calculate(operation="divide", a=100.0, b=0.0)
    assert res_div.success is False
    assert res_div.error is not None
    assert "zero" in res_div.error.lower()

    # Percentage with b=0 should fail gracefully
    res_pct = calculate(operation="percentage", a=100.0, b=0.0)
    assert res_pct.success is False
    assert res_pct.error is not None
    assert "zero" in res_pct.error.lower()


def test_invalid_operation():
    res = calculate(operation="exponent", a=2.0, b=3.0)
    assert res.success is False
    assert res.error is not None
    assert "unsupported operation" in res.error.lower()


def test_json_schema_generation():
    tool = CalculatorTool()
    schema = tool.to_json_schema()
    assert schema["name"] == "calculate"
    assert "description" in schema
    assert "parameters" in schema
    props = schema["parameters"]["properties"]
    assert "operation" in props
    assert "a" in props
    assert "b" in props


def test_calculator_input_validation():
    # Test passing missing/invalid input to tool.run()
    res = calculator_tool.run(operation="add", a="invalid_number")
    assert res.success is False
    assert "invalid" in res.error.lower()
