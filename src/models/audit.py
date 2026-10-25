from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.models.enums import AuditClassification, RiskLevel

class AuditFinding(BaseModel):
    """Detailed finding produced by auditing an expense item."""
    model_config = ConfigDict(use_enum_values=True, populate_by_name=True)

    finding_id: Optional[str] = Field(None, description="Unique finding ID")
    item_id: str = Field(..., description="Referenced expense item ID")
    employee_id: Optional[str] = Field(None, description="Referenced employee ID")
    expense_type: Optional[str] = Field(None, description="Identified expense type/category (COURSE, WFH_SETUP, TRAVEL, SOFTWARE_LICENSE, UNKNOWN)")
    classification: AuditClassification = Field(..., description="Audit classification category")
    reasoning: str = Field(..., description="Detailed explanation/justification of finding")
    calculated_variance: float = Field(0.0, description="Amount in excess of policy/approval")
    evidence: List[str] = Field(default_factory=list, description="List of evidence strings/documents")
    risk_level: RiskLevel = Field(RiskLevel.LOW, description="Assessed risk level")
    action_recommended: Optional[str] = Field(None, description="Recommended remediation action")
    checks_performed: List[str] = Field(default_factory=list, description="List of audit checks performed")
    checks_skipped: List[str] = Field(default_factory=list, description="List of audit checks skipped")
    approval_status: Optional[str] = Field(None, description="Approval status when applicable (APPROVED, NOT_REQUIRED, MISSING_APPROVAL, N/A)")
    routing_path: List[str] = Field(default_factory=list, description="Selected branching audit path steps")



class AuditSummary(BaseModel):
    """Overall summary statistics for an audit session."""
    model_config = ConfigDict(populate_by_name=True)

    session_id: Optional[str] = Field(None, description="Audit session identifier")
    total_items_audited: int = Field(0, description="Total count of expense line items audited")
    total_claimed_amount: float = Field(0.0, description="Total claimed monetary value")
    total_compliant_amount: float = Field(0.0, description="Total compliant monetary value")
    compliant_count: int = Field(0, description="Count of compliant expense line items")
    exception_count: int = Field(0, description="Count of policy exceptions/anomalies found")
    findings: List[AuditFinding] = Field(default_factory=list, description="Collection of audit findings")
    prompt_tokens: int = Field(0, description="Total prompt/input tokens consumed")
    completion_tokens: int = Field(0, description="Total completion/output tokens generated")
    total_tokens: int = Field(0, description="Total tokens consumed across all LLM turns")
    estimated_cost_usd: float = Field(0.0, description="Estimated inference cost in USD")
    estimated_cost_inr: float = Field(0.0, description="Estimated inference cost in INR")
    llm_turns_count: int = Field(0, description="Total number of LLM inference calls made")

