from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.models.enums import ApprovalStatus

class ManagerApproval(BaseModel):
    """Manager pre-approval entity model."""
    model_config = ConfigDict(populate_by_name=True)

    approval_id: str = Field(..., description="Unique approval reference ID")
    employee_id: str = Field(..., description="Employee ID receiving approval")
    employee_name: Optional[str] = Field(None, description="Employee full name")
    category: str = Field(..., description="Expense category approved")
    max_approved_amount: float = Field(..., description="Maximum approved amount")
    approved_by: str = Field(..., description="Name or ID of approving manager")
    approval_date: Optional[str] = Field(None, description="Date approval was granted (YYYY-MM-DD)")
    reason: Optional[str] = Field(None, description="Business justification for exception")
    status: Union[ApprovalStatus, str] = Field(ApprovalStatus.APPROVED, description="Approval status")

    @field_validator("max_approved_amount")
    @classmethod
    def validate_max_approved_amount(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Max approved amount cannot be negative")
        return v
