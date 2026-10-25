from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, AliasChoices

class ExpenseItem(BaseModel):
    """Expense line item entity model."""
    model_config = ConfigDict(populate_by_name=True)

    item_id: str = Field(
        ...,
        validation_alias=AliasChoices("item_id", "expense_id"),
        description="Unique identifier for the expense line item"
    )
    employee_id: str = Field(..., description="ID of the employee claiming the expense")
    employee_name: Optional[str] = Field(None, description="Name of the employee")
    date: str = Field(..., description="Expense date (YYYY-MM-DD)")
    category: str = Field(..., description="Expense category (e.g. Hotel, Meals, Taxi)")
    claimed_amount: float = Field(
        ...,
        validation_alias=AliasChoices("claimed_amount", "amount"),
        description="Claimed amount in local currency"
    )
    currency: str = Field("INR", description="Currency code (e.g. INR, USD)")
    merchant: Optional[str] = Field(None, description="Merchant/Vendor name")
    description: Optional[str] = Field(None, description="Detailed description/reason")
    receipt_attached: bool = Field(True, description="Flag indicating if receipt is attached")
    receipt_path: Optional[str] = Field(None, description="Relative path to receipt image/PDF")
    status: Optional[str] = Field("SUBMITTED", description="Expense claim status")

    @field_validator("claimed_amount")
    @classmethod
    def validate_claimed_amount(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Claimed amount cannot be negative")
        return v
