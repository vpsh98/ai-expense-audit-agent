from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.models.agent import ToolResult

class CalculateInput(BaseModel):
    """Input schema for the calculate tool."""
    operation: str = Field(
        ...,
        description="Arithmetic operation: 'add', 'subtract', 'multiply', 'divide', or 'percentage'"
    )
    a: float = Field(..., description="First numeric operand (e.g., claimed amount)")
    b: float = Field(..., description="Second numeric operand (e.g., policy cap or per-diem days)")


class CalculatorTool(BaseTool):
    """Deterministic calculator tool for expense auditing math."""

    name: str = "calculate"
    description: str = (
        "Perform deterministic arithmetic operations (add, subtract, multiply, divide, percentage) "
        "to calculate variances, daily rates, per-diem totals, and percentages without mathematical hallucination."
    )
    args_schema = CalculateInput

    def _run(self, operation: str, a: float, b: float) -> Any:
        op = operation.strip().lower()

        if op == "add":
            val = a + b
        elif op == "subtract":
            val = a - b
        elif op == "multiply":
            val = a * b
        elif op == "divide":
            if b == 0:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error="Division by zero is not allowed"
                )
            val = a / b
        elif op == "percentage":
            if b == 0:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error="Division by zero in percentage calculation"
                )
            val = ((a - b) / b) * 100.0
        else:
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=f"Unsupported operation '{operation}'. Supported operations: add, subtract, multiply, divide, percentage."
            )

        rounded_val = round(val, 2)
        formatted_str = f"{rounded_val:.2f}"

        return {
            "value": rounded_val,
            "formatted_result": formatted_str,
            "operation": op,
            "a": a,
            "b": b
        }


# Convenience instance and function wrapper
calculator_tool = CalculatorTool()

def calculate(operation: str, a: float, b: float) -> ToolResult:
    """Convenience helper function to run calculator tool directly."""
    return calculator_tool.run(operation=operation, a=a, b=b)
