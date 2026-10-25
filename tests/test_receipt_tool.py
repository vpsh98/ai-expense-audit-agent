import pytest
from src.data import ReceiptRepository
from src.tools import ReadReceiptTool, read_receipt, calculate
from src.models import AuditClassification, AuditFinding, RiskLevel

def test_receipt_repository():
    repo = ReceiptRepository()
    receipts = repo.get_all()
    assert len(receipts) >= 3

    # Lookup by expense ID
    rcp_101 = repo.get_by_expense_id("EXP-101")
    assert rcp_101 is not None
    assert rcp_101["receipt_id"] == "RCP-101"
    assert rcp_101["merchant"] == "Bistro Central"

    # Lookup by receipt ID
    rcp_by_id = repo.get_by_id("RCP-101")
    assert rcp_by_id is not None
    assert rcp_by_id["amount"] == 1200.0

    # Lookup by path
    rcp_by_path = repo.get_by_path("receipts/exp_101.png")
    assert rcp_by_path is not None
    assert rcp_by_path["expense_id"] == "EXP-101"


def test_read_receipt_tool():
    res = read_receipt(expense_id="EXP-101")
    assert res.success is True
    assert res.result["found"] is True
    assert res.result["merchant"] == "Bistro Central"
    assert res.result["amount"] == 1200.0
    assert res.result["tax_amount"] == 108.0

    # Nonexistent receipt lookup
    res_missing = read_receipt(expense_id="EXP-999")
    assert res_missing.success is True
    assert res_missing.result["found"] is False
    assert "not found" in res_missing.result["error"].lower()


def test_receipt_mismatch_demo_validation():
    # Demo Validation: Claimed ₹2,200 vs Physical Receipt ₹1,800 -> RECEIPT_MISMATCH with ₹400 variance
    claimed_amount = 2200.0

    # Inspect physical receipt
    rcp_res = read_receipt(receipt_id="RCP-MISMATCH")
    assert rcp_res.success is True
    assert rcp_res.result["found"] is True

    receipt_amount = rcp_res.result["amount"]
    assert receipt_amount == 1800.0

    # Calculate variance
    calc_res = calculate(operation="subtract", a=claimed_amount, b=receipt_amount)
    assert calc_res.success is True
    variance = calc_res.result["value"]
    assert variance == 400.0

    # Build AuditFinding for receipt mismatch
    finding = AuditFinding(
        item_id="EXP-MISMATCH",
        classification=AuditClassification.RECEIPT_MISMATCH,
        reasoning=f"Claimed expense amount of ₹{claimed_amount:,.2f} exceeds physical receipt total of ₹{receipt_amount:,.2f} by ₹{variance:,.2f}.",
        calculated_variance=variance,
        evidence=[f"Claimed: ₹{claimed_amount:,.2f}", f"Receipt Total: ₹{receipt_amount:,.2f}"],
        risk_level=RiskLevel.HIGH,
        action_recommended=f"Recoup ₹{variance:,.2f} overclaim."
    )

    assert finding.classification == AuditClassification.RECEIPT_MISMATCH
    assert finding.calculated_variance == 400.0


def test_missing_document_detection():
    # Test missing mandatory receipt detection
    finding = AuditFinding(
        item_id="EXP-NO-RCP",
        classification=AuditClassification.MISSING_DOCUMENT,
        reasoning="Hotel expense of ₹7,500 exceeds mandatory receipt threshold of ₹500, but no receipt was attached.",
        calculated_variance=7500.0,
        evidence=["Policy requires itemized receipt above ₹500", "No receipt file attached"],
        risk_level=RiskLevel.HIGH,
        action_recommended="Request employee submit itemized hotel bill."
    )

    assert finding.classification == AuditClassification.MISSING_DOCUMENT
    assert finding.calculated_variance == 7500.0
