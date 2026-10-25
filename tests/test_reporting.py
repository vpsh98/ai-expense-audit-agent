import json
from pathlib import Path
import pytest

from src.models import AuditSummary, AuditFinding, AuditClassification, RiskLevel
from src.reporting import (
    MarkdownReportGenerator,
    JSONReportGenerator,
    HTMLPDFReportGenerator,
)
from src.agent import ExpenseAuditAgent, LLMClient

@pytest.fixture
def sample_audit_summary() -> AuditSummary:
    finding1 = AuditFinding(
        finding_id="FND-101",
        item_id="EXP-101",
        employee_id="EMP001",
        classification=AuditClassification.COMPLIANT,
        reasoning="Expense of ₹1,200 is within policy limit of ₹1,500.",
        calculated_variance=0.0,
        evidence=["Claimed: ₹1,200", "Policy Cap: ₹1,500"],
        risk_level=RiskLevel.LOW,
        action_recommended="Approve for reimbursement."
    )
    finding2 = AuditFinding(
        finding_id="FND-105",
        item_id="EXP-105",
        employee_id="EMP002",
        classification=AuditClassification.MISSING_APPROVAL,
        reasoning="Taxi expense of ₹4,500 exceeds limit of ₹3,000 without prior manager approval.",
        calculated_variance=1500.0,
        evidence=["Policy Cap: ₹3,000", "No approval record found"],
        risk_level=RiskLevel.HIGH,
        action_recommended="Request retro-approval or recoup ₹1,500."
    )
    return AuditSummary(
        session_id="SESS-TEST-01",
        total_items_audited=2,
        total_claimed_amount=5700.0,
        total_compliant_amount=1200.0,
        compliant_count=1,
        exception_count=1,
        findings=[finding1, finding2]
    )


def test_markdown_report_generator(sample_audit_summary: AuditSummary):
    gen = MarkdownReportGenerator()
    md_text = gen.generate(sample_audit_summary)

    assert "# 📋 AI Expense Audit Executive Report" in md_text
    assert "SESS-TEST-01" in md_text
    assert "Total Line Items Audited" in md_text
    assert "₹5,700.00" in md_text
    assert "₹1,500.00" in md_text  # Excess variance
    assert "| `EXP-101` | `COMPLIANT` |" in md_text
    assert "| `EXP-105` | `MISSING_APPROVAL` |" in md_text
    assert "Evidence Citations:" in md_text
    assert "Policy Cap: ₹3,000" in md_text


def test_markdown_report_rajesh_kumar_demo_validation():
    # Demo Validation: Run agent for Rajesh Kumar and generate Markdown report
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client)
    summary = agent.run_audit("Audit Rajesh Kumar's September expenses")

    gen = MarkdownReportGenerator()
    md = gen.generate(summary)

    assert "Rajesh Kumar" in md or "EMP001" in md or "EXP-101" in md
    assert "Audit Findings Overview" in md
    assert "Detailed Finding Analysis" in md


def test_json_report_generator(sample_audit_summary: AuditSummary):
    gen = JSONReportGenerator()
    json_str = gen.generate(sample_audit_summary)

    data = json.loads(json_str)
    assert data["session_id"] == "SESS-TEST-01"
    metrics = data["summary_metrics"]
    assert metrics["total_items_audited"] == 2
    assert metrics["total_claimed_amount"] == 5700.0
    assert metrics["total_excess_variance"] == 1500.0
    assert metrics["missing_approvals_count"] == 1

    findings = data["findings"]
    assert len(findings) == 2
    assert findings[1]["classification"] == "MISSING_APPROVAL"


def test_html_pdf_report_generator(sample_audit_summary: AuditSummary):
    gen = HTMLPDFReportGenerator()
    html_text = gen.generate(sample_audit_summary)

    assert "<!DOCTYPE html>" in html_text
    assert "Expense Audit Executive Report" in html_text
    assert "SESS-TEST-01" in html_text
    assert "₹5,700.00" in html_text
    assert "EXP-105" in html_text
    assert "badge-high" in html_text


def test_export_to_file(sample_audit_summary: AuditSummary, tmp_path: Path):
    md_path = tmp_path / "report.md"
    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"

    MarkdownReportGenerator().export_to_file(sample_audit_summary, md_path)
    JSONReportGenerator().export_to_file(sample_audit_summary, json_path)
    HTMLPDFReportGenerator().export_to_file(sample_audit_summary, html_path)

    assert md_path.exists() and md_path.stat().st_size > 0
    assert json_path.exists() and json_path.stat().st_size > 0
    assert html_path.exists() and html_path.stat().st_size > 0
