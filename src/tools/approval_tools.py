from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.data import ApprovalRepository

class CheckApprovalInput(BaseModel):
    """Input schema for check_approval tool."""
    employee_id: str = Field(..., description="Employee ID (e.g. EMP003)")
    category: str = Field(..., description="Expense category (e.g. Hotel, Flight)")
    amount: float = Field(..., description="Claimed expense amount to verify")
    date: Optional[str] = Field(None, description="Optional expense date YYYY-MM-DD")


class CheckApprovalTool(BaseTool):
    """Tool to verify if prior manager approval exists for an expense item."""

    name: str = "check_approval"
    description: str = (
        "Check whether prior manager approval exists for an expense item exceeding standard policy limits."
    )
    args_schema = CheckApprovalInput

    def __init__(self, approval_repo: Optional[ApprovalRepository] = None):
        super().__init__()
        self.approval_repo = approval_repo or ApprovalRepository()

    def _run(
        self,
        employee_id: str,
        category: str,
        amount: float,
        date: Optional[str] = None
    ) -> Any:
        # Get matching approval
        approval = self.approval_repo.get_approval_for_expense(
            employee_id=employee_id,
            category=category,
            amount=amount
        )

        if not approval:
            # Check if any approval exists for employee & category even if amount exceeds it
            all_apps = self.approval_repo.get_by_employee_and_category(employee_id, category)
            if all_apps:
                app_info = all_apps[0]
                max_approved = float(app_info.get("max_approved_amount", 0.0))
                formatted_str = (
                    f"NO VALID APPROVAL: Pre-approval '{app_info.get('approval_id')}' exists up to "
                    f"₹{max_approved:,.2f}, but claimed amount ₹{amount:,.2f} exceeds approved limit."
                )
                return {
                    "has_approval": False,
                    "reason": "Claimed amount exceeds pre-approved limit",
                    "existing_approval": app_info,
                    "formatted_result": formatted_str
                }
            else:
                formatted_str = (
                    f"NO APPROVAL FOUND: No prior manager approval recorded for Employee '{employee_id}', "
                    f"Category '{category}', Amount ₹{amount:,.2f}."
                )
                return {
                    "has_approval": False,
                    "reason": "No pre-approval recorded",
                    "formatted_result": formatted_str
                }

        max_app = float(approval.get("max_approved_amount", 0.0))
        formatted_str = (
            f"APPROVAL VERIFIED ({approval.get('approval_id')}):\n"
            f"- Employee: {approval.get('employee_name')} ({employee_id})\n"
            f"- Category: {category}\n"
            f"- Claimed Amount: ₹{amount:,.2f} (Pre-approved up to ₹{max_app:,.2f})\n"
            f"- Approved By: {approval.get('approved_by')}\n"
            f"- Reason: {approval.get('reason', 'N/A')}\n"
            f"- Status: {approval.get('status')}"
        )

        return {
            "has_approval": True,
            "approval_id": approval.get("approval_id"),
            "approved_by": approval.get("approved_by"),
            "max_approved_amount": max_app,
            "status": approval.get("status"),
            "reason": approval.get("reason"),
            "approval_details": approval,
            "formatted_result": formatted_str
        }


# Global tool instance and function helper
check_approval_tool = CheckApprovalTool()

def check_approval(
    employee_id: str,
    category: str,
    amount: float,
    date: Optional[str] = None
):
    """Convenience function wrapper for check_approval tool."""
    return check_approval_tool.run(
        employee_id=employee_id,
        category=category,
        amount=amount,
        date=date
    )
