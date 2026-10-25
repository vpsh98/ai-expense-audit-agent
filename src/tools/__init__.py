"""Agent tools package."""
from src.tools.base import BaseTool
from src.tools.calculator import CalculatorTool, calculator_tool, calculate
from src.tools.employee_tools import GetEmployeeDetailsTool, get_employee_details_tool, get_employee_details
from src.tools.expense_tools import ReadExpenseReportTool, read_expense_report_tool, read_expense_report
from src.tools.policy_tools import SearchExpensePolicyTool, search_expense_policy_tool, search_expense_policy
from src.tools.approval_tools import CheckApprovalTool, check_approval_tool, check_approval
from src.tools.receipt_tools import ReadReceiptTool, read_receipt_tool, read_receipt

__all__ = [
    "BaseTool",
    "CalculatorTool",
    "calculator_tool",
    "calculate",
    "GetEmployeeDetailsTool",
    "get_employee_details_tool",
    "get_employee_details",
    "ReadExpenseReportTool",
    "read_expense_report_tool",
    "read_expense_report",
    "SearchExpensePolicyTool",
    "search_expense_policy_tool",
    "search_expense_policy",
    "CheckApprovalTool",
    "check_approval_tool",
    "check_approval",
    "ReadReceiptTool",
    "read_receipt_tool",
    "read_receipt",
]
