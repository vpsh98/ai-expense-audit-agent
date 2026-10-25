import pytest
from src.models import AuditSummary, AuditFinding, AuditClassification, RiskLevel
from src.ui.components import get_classification_badge
from src.reporting import MarkdownReportGenerator, JSONReportGenerator, HTMLPDFReportGenerator

def test_get_classification_badge():
    assert "🟢" in get_classification_badge(AuditClassification.COMPLIANT)
    assert "🔵" in get_classification_badge(AuditClassification.POLICY_EXCEPTION)
    assert "🔴" in get_classification_badge(AuditClassification.MISSING_APPROVAL)
    assert "🟠" in get_classification_badge(AuditClassification.RECEIPT_MISMATCH)
    assert "📄" in get_classification_badge(AuditClassification.MISSING_DOCUMENT)
    assert "⚠️" in get_classification_badge(AuditClassification.REQUIRES_REVIEW)
    assert "MISSING APPROVAL" in get_classification_badge("MISSING_APPROVAL")


def test_ui_results_summary_preparation():
    finding = AuditFinding(
        finding_id="FND-104",
        item_id="EXP-104",
        employee_id="EMP003",
        classification=AuditClassification.POLICY_EXCEPTION,
        reasoning="Hotel expense of ₹12,000 exceeds policy cap of ₹8,000 but has pre-approval APP-2026-001.",
        calculated_variance=4000.0,
        evidence=["Pre-approval APP-2026-001 approved up to ₹15,000"],
        risk_level=RiskLevel.LOW,
        action_recommended="Approve exception."
    )
    summary = AuditSummary(
        session_id="SESS-UI-TEST",
        total_items_audited=1,
        total_claimed_amount=12000.0,
        total_compliant_amount=12000.0,
        compliant_count=1,
        exception_count=1,
        findings=[finding]
    )

    # Test report outputs available for UI downloads
    md_output = MarkdownReportGenerator().generate(summary)
    json_output = JSONReportGenerator().generate(summary)
    html_output = HTMLPDFReportGenerator().generate(summary)

    assert "EXP-104" in md_output
    assert "SESS-UI-TEST" in json_output
    assert "12,000.00" in html_output
