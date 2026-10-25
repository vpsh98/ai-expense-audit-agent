from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.data import ExpenseRepository

class ReadExpenseReportInput(BaseModel):
    """Input schema for read_expense_report tool."""
    employee_id: str = Field(..., description="Employee ID (e.g. EMP001)")
    start_date: Optional[str] = Field(None, description="Start date filter (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date filter (YYYY-MM-DD)")
    period: Optional[str] = Field(None, description="Period filter (YYYY-MM or YYYY-MM-DD)")


class ReadExpenseReportTool(BaseTool):
    """Tool to read expense line items for an employee."""

    name: str = "read_expense_report"
    description: str = (
        "Retrieve expense line items submitted by an employee, optionally filtered by date range or period."
    )
    args_schema = ReadExpenseReportInput

    def __init__(self, expense_repo: Optional[ExpenseRepository] = None):
        super().__init__()
        self.expense_repo = expense_repo or ExpenseRepository()

    def _run(
        self,
        employee_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> Any:
        all_emp_expenses = self.expense_repo.get_by_employee_id(employee_id)

        # Handle period filter (e.g. "2026-09") supporting YYYY-MM-DD and DD-MM-YYYY formats
        if period and not start_date and not end_date:
            parts = period.split("-")
            year, month = (parts[0], parts[1]) if len(parts) == 2 else ("", "")
            filtered = []
            for exp in all_emp_expenses:
                exp_date = str(exp.get("date", "")).strip()
                if exp_date.startswith(period):
                    filtered.append(exp)
                elif year and month and exp_date.endswith(f"-{year}") and f"-{month}-" in exp_date:
                    filtered.append(exp)
        elif start_date and end_date:
            filtered = self.expense_repo.get_expenses_by_date_range(
                start_date=start_date,
                end_date=end_date,
                employee_id=employee_id
            )
        else:
            filtered = all_emp_expenses

        total_amount = sum(float(exp.get("amount", 0.0)) for exp in filtered)
        count = len(filtered)

        lines = [f"Expense report for Employee '{employee_id}' ({count} items, Total: ₹{total_amount:,.2f}):"]
        for exp in filtered:
            lines.append(
                f"- [{exp.get('expense_id')}] {exp.get('date')} | {exp.get('category')}: "
                f"₹{float(exp.get('amount', 0.0)):,.2f} at {exp.get('merchant', 'N/A')} ({exp.get('description', '')})"
            )

        formatted_str = "\n".join(lines)

        return {
            "employee_id": employee_id,
            "count": count,
            "total_amount": round(total_amount, 2),
            "expenses": filtered,
            "formatted_result": formatted_str
        }


# Global tool instance and function helper
read_expense_report_tool = ReadExpenseReportTool()

def read_expense_report(
    employee_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = None
):
    """Convenience function wrapper for read_expense_report tool."""
    return read_expense_report_tool.run(
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        period=period
    )
