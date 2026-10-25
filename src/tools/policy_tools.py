from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.data import PolicyRepository

class SearchExpensePolicyInput(BaseModel):
    """Input schema for search_expense_policy tool."""
    category: str = Field(..., description="Expense category to search policy for (e.g. COURSE, WFH_SETUP, Hotel, Taxi, Flight)")
    employee_grade: Optional[str] = Field(None, description="Optional employee grade level")
    item: Optional[str] = Field(None, description="Optional specific item name or type (e.g. monitor, keyboard) for WFH_SETUP")


class SearchExpensePolicyTool(BaseTool):
    """Tool to search corporate spending policies and limits."""

    name: str = "search_expense_policy"
    description: str = (
        "Search corporate spending policy limits, receipt requirements, and approval criteria by expense category."
    )
    args_schema = SearchExpensePolicyInput

    def __init__(self, policy_repo: Optional[PolicyRepository] = None):
        super().__init__()
        self.policy_repo = policy_repo or PolicyRepository()

    def _run(self, category: str, employee_grade: Optional[str] = None, item: Optional[str] = None) -> Any:
        policy = self.policy_repo.get_by_category(category)

        if not policy:
            return {
                "found": False,
                "category": category,
                "error": f"No spending policy defined for category '{category}'.",
                "formatted_result": f"No spending policy found for category '{category}'."
            }

        limit_amt = float(policy.get("limit_amount", 0.0))
        currency = policy.get("currency", "INR")
        unit = policy.get("limit_unit", "per_instance")
        receipt_req = policy.get("require_receipt", True)
        receipt_threshold = float(policy.get("receipt_threshold", 0.0))
        approval_above = policy.get("approval_required_above")
        approval_by_default = policy.get("approval_required_by_default", True if policy.get("category") != "WFH_SETUP" else False)
        item_limits = policy.get("item_limits", {})

        # If specific item is queried for category with item_limits (e.g. WFH_SETUP monitor)
        selected_item = None
        if item and item_limits:
            item_key = item.strip().lower()
            for k, v in item_limits.items():
                if k.lower() == item_key:
                    limit_amt = float(v)
                    selected_item = k
                    unit = "per_item"
                    break
        elif not item and isinstance(item_limits, dict):
            # Check if category itself is an item
            cat_key = category.strip().lower()
            for k, v in item_limits.items():
                if k.lower() == cat_key:
                    limit_amt = float(v)
                    selected_item = k
                    unit = "per_item"
                    break

        lines = [f"Policy for '{policy.get('category')}':"]
        if selected_item:
            lines.append(f"- Specific Item: {selected_item.capitalize()} (Limit: ₹{limit_amt:,.2f})")
        else:
            lines.append(f"- Max Spending Limit: ₹{limit_amt:,.2f} ({unit})")
        lines.append(f"- Currency: {currency}")
        lines.append(f"- Receipt Mandatory: {'Yes' if receipt_req else 'No'} (above ₹{receipt_threshold:,.2f})")

        if policy.get("category") == "WFH_SETUP":
            lines.append("- Manager Approval: NOT required by default (skip approval tool)")
        elif policy.get("category") == "COURSE":
            lines.append("- Manager Approval: Required ONLY when amount > ₹10,000 (skip if <= ₹10,000)")
        elif approval_above is not None:
            lines.append(f"- Manager Approval: Required above ₹{float(approval_above):,.2f}")

        if policy.get("description"):
            lines.append(f"- Description: {policy.get('description')}")

        formatted = "\n".join(lines)

        return {
            "found": True,
            "category": policy.get("category"),
            "item": selected_item or item,
            "limit_amount": limit_amt,
            "max_limit": limit_amt,
            "limit_unit": unit,
            "currency": currency,
            "require_receipt": receipt_req,
            "receipt_threshold": receipt_threshold,
            "approval_required_above": approval_above,
            "approval_required_by_default": approval_by_default,
            "item_limits": item_limits,
            "description": policy.get("description"),
            "formatted_result": formatted
        }


# Global tool instance and function helper
search_expense_policy_tool = SearchExpensePolicyTool()

def search_expense_policy(category: str, employee_grade: Optional[str] = None, item: Optional[str] = None):
    """Convenience function wrapper for search_expense_policy tool."""
    return search_expense_policy_tool.run(category=category, employee_grade=employee_grade, item=item)
