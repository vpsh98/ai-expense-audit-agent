import json
import pytest
from pydantic import ValidationError

from src.models import (
    AuditClassification,
    ExpenseCategory,
    ApprovalStatus,
    RiskLevel,
    Employee,
    ExpenseItem,
    PolicyRule,
    ManagerApproval,
    AuditFinding,
    AuditSummary,
    ToolResult,
    AgentStep,
)

def test_audit_classification_enum():
    assert AuditClassification.COMPLIANT == "COMPLIANT"
    assert AuditClassification.MISSING_APPROVAL == "MISSING_APPROVAL"
    assert AuditClassification.POLICY_EXCEPTION == "POLICY_EXCEPTION"
    assert AuditClassification.RECEIPT_MISMATCH == "RECEIPT_MISMATCH"
    assert AuditClassification.MISSING_DOCUMENT == "MISSING_DOCUMENT"
    assert AuditClassification.REQUIRES_REVIEW == "REQUIRES_REVIEW"


def test_employee_model():
    emp = Employee(
        employee_id="EMP001",
        name="Rajesh Kumar",
        department="Sales",
        designation="Senior Account Executive",
        manager_name="Sunita Rao"
    )
    assert emp.employee_id == "EMP001"
    assert emp.name == "Rajesh Kumar"

    json_str = emp.model_dump_json()
    reloaded = Employee.model_validate_json(json_str)
    assert reloaded == emp


def test_expense_item_model_and_validation():
    # Test valid item
    item = ExpenseItem(
        expense_id="EXP-101",
        employee_id="EMP001",
        date="2026-09-10",
        category="Meals",
        claimed_amount=1200.0,
        description="Client lunch"
    )
    assert item.item_id == "EXP-101"
    assert item.claimed_amount == 1200.0

    # Lossless JSON roundtrip
    json_data = item.model_dump_json()
    reloaded = ExpenseItem.model_validate_json(json_data)
    assert reloaded.item_id == item.item_id
    assert reloaded.claimed_amount == item.claimed_amount

    # Test invalid negative amount validation error
    with pytest.raises(ValidationError):
        ExpenseItem(
            expense_id="EXP-ERR",
            employee_id="EMP001",
            date="2026-09-10",
            category="Meals",
            claimed_amount=-500.0
        )


def test_policy_rule_model():
    policy = PolicyRule(
        category="Hotel",
        limit_amount=8000.0,
        limit_unit="per_night",
        require_receipt=True
    )
    assert policy.category == "Hotel"
    assert policy.max_amount == 8000.0

    with pytest.raises(ValidationError):
        PolicyRule(category="Hotel", limit_amount=-100.0)


def test_manager_approval_model():
    approval = ManagerApproval(
        approval_id="APP-001",
        employee_id="EMP003",
        category="Hotel",
        max_approved_amount=15000.0,
        approved_by="Sunita Rao"
    )
    assert approval.approval_id == "APP-001"
    assert approval.max_approved_amount == 15000.0
    assert approval.status == ApprovalStatus.APPROVED

    with pytest.raises(ValidationError):
        ManagerApproval(
            approval_id="APP-ERR",
            employee_id="EMP003",
            category="Hotel",
            max_approved_amount=-50.0,
            approved_by="Sunita Rao"
        )


def test_audit_finding_and_demo_validation():
    finding = AuditFinding(
        finding_id="FND-105",
        item_id="EXP-105",
        employee_id="EMP002",
        classification=AuditClassification.MISSING_APPROVAL,
        reasoning="Taxi expense of ₹4,500 exceeds policy limit of ₹3,000 without prior manager approval.",
        calculated_variance=1500.0,
        evidence=["Policy threshold: ₹3,000", "No approval found in approvals.json"],
        risk_level=RiskLevel.MEDIUM,
        action_recommended="Request manager retro-approval or recoup ₹1,500 excess."
    )

    assert finding.item_id == "EXP-105"
    assert finding.classification == AuditClassification.MISSING_APPROVAL
    assert finding.calculated_variance == 1500.0

    # Demo Validation: Verify clean serialization
    dumped_json = finding.model_dump_json()
    assert isinstance(dumped_json, str)
    parsed_dict = json.loads(dumped_json)
    assert parsed_dict["classification"] == "MISSING_APPROVAL"
    assert parsed_dict["calculated_variance"] == 1500.0

    # Test invalid classification string raises ValidationError
    with pytest.raises(ValidationError):
        AuditFinding(
            item_id="EXP-999",
            classification="INVALID_CLASSIFICATION",
            reasoning="Invalid classification test"
        )


def test_audit_summary_model():
    summary = AuditSummary(
        session_id="SESS-001",
        total_items_audited=5,
        total_claimed_amount=25000.0,
        total_compliant_amount=15000.0,
        compliant_count=3,
        exception_count=2
    )
    assert summary.session_id == "SESS-001"
    assert summary.exception_count == 2


def test_agent_step_and_tool_result():
    tool_res = ToolResult(
        tool_name="get_policy_limit",
        success=True,
        result={"limit_amount": 8000.0}
    )
    step = AgentStep(
        step_number=1,
        thought="Check hotel policy limit for EMP001",
        action="get_policy_limit",
        action_input={"category": "Hotel"},
        observation=tool_res
    )
    assert step.step_number == 1
    assert step.action == "get_policy_limit"
    assert step.observation.success is True
