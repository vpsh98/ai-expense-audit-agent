from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, AliasChoices

class PolicyRule(BaseModel):
    """Company spending policy rule model."""
    model_config = ConfigDict(populate_by_name=True)

    category: str = Field(..., description="Target spending category")
    max_amount: float = Field(
        ...,
        validation_alias=AliasChoices("max_amount", "limit_amount"),
        description="Maximum policy monetary limit"
    )
    limit_unit: str = Field("per_instance", description="Limit unit (per_night, per_day, per_trip, etc.)")
    currency: str = Field("INR", description="Currency code")
    require_receipt: bool = Field(True, description="Whether receipt is mandatory")
    receipt_threshold: Optional[float] = Field(0.0, description="Amount above which receipt is mandatory")
    approval_required_above: Optional[float] = Field(None, description="Amount threshold requiring prior manager approval")
    approval_required_by_default: Optional[bool] = Field(True, description="Whether manager approval is required by default")
    item_limits: Optional[dict] = Field(default_factory=dict, description="Item-specific monetary limits (e.g. for WFH equipment)")
    description: Optional[str] = Field(None, description="Policy text description")

    @field_validator("max_amount")
    @classmethod
    def validate_max_amount(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Policy max amount cannot be negative")
        return v
