import json
from pathlib import Path
import pytest

from src.agent import ExpenseAuditAgent, LLMClient, default_registry
from src.tools import (
    calculate,
    search_expense_policy,
    check_approval,
    read_receipt,
    get_employee_details,
    read_expense_report,
)
from src.models import (
    AuditClassification,
    AuditFinding,
    AuditSummary,
    RiskLevel,
)

def test_scenario_a_compliant():
    """Scenario A: Expense within policy limit (Taxi ₹2,500 < ₹3,000 policy cap)."""
    pol_res = search_expense_policy(category="Taxi")
    assert pol_res.success is True
    limit = pol_res.result["limit_amount"]
    assert limit == 3000.0

    claimed_amount = 2500.0
    calc_res = calculate(operation="subtract", a=claimed_amount, b=limit)
    assert calc_res.success is True
    variance = calc_res.result["value"]
    assert variance == -500.0  # Under limit by 500

    finding = AuditFinding(
        item_id="EXP-SCEN-A",
        employee_id="EMP001",
        classification=AuditClassification.COMPLIANT,
        reasoning=f"Taxi expense of ₹{claimed_amount:,.2f} is within policy cap of ₹{limit:,.2f}.",
        calculated_variance=0.0,
        evidence=[f"Claimed: ₹{claimed_amount:,.2f}", f"Policy Cap: ₹{limit:,.2f}"],
        risk_level=RiskLevel.LOW,
        action_recommended="Approve reimbursement."
    )

    assert finding.classification == AuditClassification.COMPLIANT
    assert finding.calculated_variance == 0.0


def test_scenario_b_policy_exception_approved():
    """Scenario B: Hotel expense ₹12,000 > ₹8,000 cap, but verified manager pre-approval APP-2026-001 exists."""
    claimed_amount = 12000.0
    pol_res = search_expense_policy(category="Hotel")
    limit = pol_res.result["limit_amount"]
    assert limit == 8000.0

    calc_res = calculate(operation="subtract", a=claimed_amount, b=limit)
    variance = calc_res.result["value"]
    assert variance == 4000.0

    app_res = check_approval(employee_id="EMP003", category="Hotel", amount=claimed_amount)
    assert app_res.success is True
    assert app_res.result["has_approval"] is True
    assert app_res.result["approval_id"] == "APP-2026-001"

    finding = AuditFinding(
        item_id="EXP-104",
        employee_id="EMP003",
        classification=AuditClassification.POLICY_EXCEPTION,
        reasoning=f"Hotel expense of ₹{claimed_amount:,.2f} exceeds cap of ₹{limit:,.2f} by ₹{variance:,.2f}, but has valid pre-approval APP-2026-001.",
        calculated_variance=variance,
        evidence=[f"Approval ID: {app_res.result['approval_id']}", f"Max Approved: ₹{app_res.result['max_approved_amount']:,.2f}"],
        risk_level=RiskLevel.LOW,
        action_recommended="Approve exception under pre-approval."
    )

    assert finding.classification == AuditClassification.POLICY_EXCEPTION
    assert finding.calculated_variance == 4000.0


def test_scenario_c_missing_approval_violation():
    """Scenario C: Taxi expense ₹4,500 > ₹3,000 cap without manager pre-approval."""
    claimed_amount = 4500.0
    pol_res = search_expense_policy(category="Taxi")
    limit = pol_res.result["limit_amount"]
    assert limit == 3000.0

    calc_res = calculate(operation="subtract", a=claimed_amount, b=limit)
    variance = calc_res.result["value"]
    assert variance == 1500.0

    app_res = check_approval(employee_id="EMP002", category="Taxi", amount=claimed_amount)
    assert app_res.success is True
    assert app_res.result["has_approval"] is False

    finding = AuditFinding(
        item_id="EXP-105",
        employee_id="EMP002",
        classification=AuditClassification.MISSING_APPROVAL,
        reasoning=f"Taxi expense of ₹{claimed_amount:,.2f} exceeds policy limit of ₹{limit:,.2f} by ₹{variance:,.2f} without manager pre-approval.",
        calculated_variance=variance,
        evidence=[f"Claimed: ₹{claimed_amount:,.2f}", f"Policy Cap: ₹{limit:,.2f}", "No approval recorded"],
        risk_level=RiskLevel.HIGH,
        action_recommended=f"Request retro-approval or recoup ₹{variance:,.2f} excess."
    )

    assert finding.classification == AuditClassification.MISSING_APPROVAL
    assert finding.calculated_variance == 1500.0


def test_scenario_d_receipt_mismatch():
    """Scenario D: Claimed ₹2,200 vs physical receipt total ₹1,800."""
    claimed_amount = 2200.0
    rcp_res = read_receipt(receipt_id="RCP-MISMATCH")
    assert rcp_res.success is True
    assert rcp_res.result["found"] is True

    receipt_amount = rcp_res.result["amount"]
    assert receipt_amount == 1800.0

    calc_res = calculate(operation="subtract", a=claimed_amount, b=receipt_amount)
    variance = calc_res.result["value"]
    assert variance == 400.0

    finding = AuditFinding(
        item_id="EXP-MISMATCH",
        classification=AuditClassification.RECEIPT_MISMATCH,
        reasoning=f"Claimed expense of ₹{claimed_amount:,.2f} exceeds physical receipt total of ₹{receipt_amount:,.2f} by ₹{variance:,.2f}.",
        calculated_variance=variance,
        evidence=[f"Claimed Amount: ₹{claimed_amount:,.2f}", f"Receipt Total: ₹{receipt_amount:,.2f}"],
        risk_level=RiskLevel.HIGH,
        action_recommended=f"Recoup ₹{variance:,.2f} overclaim."
    )

    assert finding.classification == AuditClassification.RECEIPT_MISMATCH
    assert finding.calculated_variance == 400.0


def test_scenario_e_missing_document():
    """Scenario E: Hotel expense ₹7,500 lacking required receipt attached."""
    claimed_amount = 7500.0
    pol_res = search_expense_policy(category="Hotel")
    receipt_required = pol_res.result["require_receipt"]
    threshold = pol_res.result["receipt_threshold"]
    assert receipt_required is True
    assert claimed_amount > threshold

    rcp_res = read_receipt(expense_id="EXP-NO-RECEIPT")
    assert rcp_res.success is True
    assert rcp_res.result["found"] is False

    finding = AuditFinding(
        item_id="EXP-NO-RECEIPT",
        classification=AuditClassification.MISSING_DOCUMENT,
        reasoning=f"Hotel expense of ₹{claimed_amount:,.2f} exceeds mandatory receipt threshold of ₹{threshold:,.2f}, but no itemized receipt was attached.",
        calculated_variance=claimed_amount,
        evidence=[f"Policy requires receipt above ₹{threshold:,.2f}", "No receipt attached"],
        risk_level=RiskLevel.HIGH,
        action_recommended="Request employee provide physical hotel folio."
    )

    assert finding.classification == AuditClassification.MISSING_DOCUMENT
    assert finding.calculated_variance == 7500.0


def test_full_agent_end_to_end_audit_execution():
    """End-to-End Test: Execute audit agent on demo request and verify complete trace."""
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    summary = agent.run_audit("Audit Rajesh Kumar's September expenses")

    assert isinstance(summary, AuditSummary)
    assert summary.total_items_audited > 0
    assert len(summary.findings) > 0

    trace = agent.get_execution_trace()
    tool_names = [step.action for step in trace if step.action]
    assert "get_employee_details" in tool_names
    assert "read_expense_report" in tool_names
    assert "search_expense_policy" in tool_names
    assert "calculate" in tool_names
    assert "check_approval" in tool_names
