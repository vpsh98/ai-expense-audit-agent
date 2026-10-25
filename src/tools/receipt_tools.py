from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.data import ReceiptRepository

class ReadReceiptInput(BaseModel):
    """Input schema for read_receipt tool."""
    receipt_id: Optional[str] = Field(None, description="Receipt reference ID (e.g. RCP-101)")
    expense_id: Optional[str] = Field(None, description="Linked expense line item ID (e.g. EXP-101)")
    receipt_path: Optional[str] = Field(None, description="Relative or absolute path to receipt file")


class ReadReceiptTool(BaseTool):
    """Tool to inspect physical/scanned receipt documents and extract metadata."""

    name: str = "read_receipt"
    description: str = (
        "Extract key details (merchant/vendor, invoice date, total amount, tax/GST, line items) "
        "from digital or scanned receipt files."
    )
    args_schema = ReadReceiptInput

    def __init__(self, receipt_repo: Optional[ReceiptRepository] = None):
        super().__init__()
        self.receipt_repo = receipt_repo or ReceiptRepository()

    def _run(
        self,
        receipt_id: Optional[str] = None,
        expense_id: Optional[str] = None,
        receipt_path: Optional[str] = None
    ) -> Any:
        if not receipt_id and not expense_id and not receipt_path:
            return {
                "found": False,
                "error": "Must provide receipt_id, expense_id, or receipt_path.",
                "formatted_result": "Error: Must provide receipt_id, expense_id, or receipt_path."
            }

        rcp = None
        if expense_id:
            rcp = self.receipt_repo.get_by_expense_id(expense_id)
        if not rcp and receipt_id:
            rcp = self.receipt_repo.get_by_id(receipt_id)
        if not rcp and receipt_path:
            rcp = self.receipt_repo.get_by_path(receipt_path)

        if not rcp:
            query = expense_id or receipt_id or receipt_path
            return {
                "found": False,
                "query": query,
                "error": f"Receipt document not found for query '{query}'.",
                "formatted_result": f"Receipt document not found for query '{query}'."
            }

        amt = float(rcp.get("amount", 0.0))
        currency = rcp.get("currency", "INR")
        merchant = rcp.get("merchant", "N/A")
        date_str = rcp.get("date", "N/A")
        tax_amt = float(rcp.get("tax_amount", 0.0))
        items = rcp.get("line_items", [])

        formatted = (
            f"Receipt Inspection ({rcp.get('receipt_id', 'N/A')}):\n"
            f"- Merchant: {merchant}\n"
            f"- Invoice Date: {date_str}\n"
            f"- Total Amount: ₹{amt:,.2f} {currency}\n"
            f"- Tax/GST: ₹{tax_amt:,.2f}\n"
            f"- Line Items Count: {len(items)}"
        )

        return {
            "found": True,
            "receipt_id": rcp.get("receipt_id"),
            "expense_id": rcp.get("expense_id"),
            "merchant": merchant,
            "date": date_str,
            "amount": amt,
            "currency": currency,
            "tax_amount": tax_amt,
            "line_items": items,
            "receipt_details": rcp,
            "formatted_result": formatted
        }


# Global tool instance and function helper
read_receipt_tool = ReadReceiptTool()

def read_receipt(
    receipt_id: Optional[str] = None,
    expense_id: Optional[str] = None,
    receipt_path: Optional[str] = None
):
    """Convenience function wrapper for read_receipt tool."""
    return read_receipt_tool.run(
        receipt_id=receipt_id,
        expense_id=expense_id,
        receipt_path=receipt_path
    )
