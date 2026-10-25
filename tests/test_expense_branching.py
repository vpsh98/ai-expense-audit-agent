import pytest
from src.agent import ExpenseAuditAgent, LLMClient, default_registry
from src.models import AuditClassification, AuditSummary, RiskLevel

def test_course_above_10000_calls_approval_check():
    """Verify that Course > ₹10,000 calls the approval tool check."""
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    # 1. Test Course above ₹10,000 with pre-approval (EXP-110, ₹18,000)
    summary = agent.run_audit("₹18,000 AWS certification course")
    assert isinstance(summary, AuditSummary)
    assert len(summary.findings) == 1

    finding = summary.findings[0]
    assert finding.expense_type == "COURSE"
    assert finding.approval_status == "APPROVED"
    assert finding.classification == AuditClassification.POLICY_EXCEPTION
    assert any("approval" in p.lower() for p in finding.checks_performed)

    trace = agent.get_execution_trace()
    tool_names = [step.action for step in trace if step.action]
    assert "search_expense_policy" in tool_names
    assert "check_approval" in tool_names
    assert "read_receipt" in tool_names

    # Check routing path structure
    assert any("✓ Category: COURSE" in p for p in finding.routing_path)
    assert any("Approval required" in p for p in finding.routing_path)
    assert any("Checking Approval" in p for p in finding.routing_path)

    # 2. Test Course above ₹10,000 without pre-approval (EXP-111, ₹15,000)
    agent_unapproved = ExpenseAuditAgent(llm_client=LLMClient(mock_mode=True), tool_registry=default_registry)
    summary_unapproved = agent_unapproved.run_audit("Audit Rajesh Kumar's course expense ₹15,000")
    # Finding for unapproved course:
    course_findings = [f for f in summary_unapproved.findings if f.item_id == "EXP-111" or "course" in f.reasoning.lower()]
    assert len(course_findings) > 0
    cf = course_findings[0]
    assert cf.expense_type == "COURSE"
    assert cf.approval_status == "MISSING_APPROVAL"
    assert cf.classification == AuditClassification.MISSING_APPROVAL
    trace_unapproved = agent_unapproved.get_execution_trace()
    assert "check_approval" in [s.action for s in trace_unapproved if s.action]


def test_course_below_or_equal_10000_skips_approval():
    """Verify that Course <= ₹10,000 skips the approval check tool."""
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    summary = agent.run_audit("₹8,000 Python course")
    assert isinstance(summary, AuditSummary)
    assert len(summary.findings) == 1

    finding = summary.findings[0]
    assert finding.expense_type == "COURSE"
    assert finding.approval_status == "NOT_REQUIRED"
    assert finding.classification == AuditClassification.COMPLIANT
    assert finding.calculated_variance == 0.0

    # Explicitly verify check_approval was NOT called in execution trace
    trace = agent.get_execution_trace()
    tool_names = [step.action for step in trace if step.action]
    assert "search_expense_policy" in tool_names
    assert "check_approval" not in tool_names
    assert "read_receipt" in tool_names

    # Verify checks skipped contains approval
    assert any("approval" in s.lower() for s in finding.checks_skipped)
    assert any("Approval not required" in p for p in finding.routing_path)


def test_wfh_setup_skips_approval():
    """Verify that WFH_SETUP skips the approval check tool by default."""
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    summary = agent.run_audit("₹12,000 monitor for home office")
    assert isinstance(summary, AuditSummary)
    assert len(summary.findings) == 1

    finding = summary.findings[0]
    assert finding.expense_type == "WFH_SETUP"
    assert finding.approval_status == "NOT_REQUIRED"
    assert finding.classification == AuditClassification.COMPLIANT
    assert finding.calculated_variance == 0.0

    # Explicitly verify check_approval was NOT called in execution trace
    trace = agent.get_execution_trace()
    tool_names = [step.action for step in trace if step.action]
    assert "search_expense_policy" in tool_names
    assert "check_approval" not in tool_names
    assert "read_receipt" in tool_names

    assert any("approval" in s.lower() for s in finding.checks_skipped)
    assert any("Approval not required" in p for p in finding.routing_path)


def test_wfh_item_above_limit_flagged():
    """Verify that WFH equipment exceeding its item reimbursement limit is flagged."""
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    summary = agent.run_audit("₹18,500 monitor for home office")
    assert isinstance(summary, AuditSummary)
    assert len(summary.findings) == 1

    finding = summary.findings[0]
    assert finding.expense_type == "WFH_SETUP"
    assert finding.approval_status == "NOT_REQUIRED"
    assert finding.classification == AuditClassification.REQUIRES_REVIEW
    assert finding.calculated_variance == 3500.0  # ₹18,500 - ₹15,000 cap = ₹3,500

    # Explicitly verify check_approval was NOT called
    trace = agent.get_execution_trace()
    tool_names = [step.action for step in trace if step.action]
    assert "search_expense_policy" in tool_names
    assert "check_approval" not in tool_names
    assert "calculate" in tool_names
    assert "read_receipt" in tool_names

    assert summary.exception_count == 1
    assert any("Monitor limit check" in p for p in finding.routing_path)
    assert any("Approval not required" in p for p in finding.routing_path)


def test_unknown_category_becomes_requires_review():
    """Verify that unknown/ambiguous expense becomes REQUIRES_REVIEW without inventing category."""
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    summary = agent.run_audit("Miscellaneous payment voucher for team items")
    assert isinstance(summary, AuditSummary)
    assert len(summary.findings) == 1

    finding = summary.findings[0]
    assert finding.expense_type == "UNKNOWN"
    assert finding.classification == AuditClassification.REQUIRES_REVIEW
    assert "Category Ambiguity Check" in finding.checks_performed
    assert "Policy Verification" in finding.checks_skipped
    assert "Approval Check" in finding.checks_skipped

    trace = agent.get_execution_trace()
    tool_names = [step.action for step in trace if step.action]
    assert "check_approval" not in tool_names
    assert summary.exception_count == 1


def test_travel_branching():
    """Verify travel expense routing and policy compliance."""
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    summary = agent.run_audit("₹22,000 flight for client onsite travel")
    assert isinstance(summary, AuditSummary)
    assert len(summary.findings) == 1

    finding = summary.findings[0]
    assert finding.expense_type == "TRAVEL"
    assert finding.classification == AuditClassification.COMPLIANT


def test_software_license_branching():
    """Verify software license expense routing and pre-approval check."""
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    summary = agent.run_audit("₹8,500 JetBrains All Products annual software license")
    assert isinstance(summary, AuditSummary)
    assert len(summary.findings) == 1

    finding = summary.findings[0]
    assert finding.expense_type == "SOFTWARE_LICENSE"
    # Over ₹5,000 threshold requires approval; APP-2026-004 covers it
    assert finding.approval_status in ("APPROVED", "MISSING_APPROVAL")
    trace = agent.get_execution_trace()
    tool_names = [step.action for step in trace if step.action]
    assert "check_approval" in tool_names


def test_routing_path_visibility_format():
    """Verify clean selected path formatting without exposing chain-of-thought."""
    llm_client = LLMClient(mock_mode=True)
    agent = ExpenseAuditAgent(llm_client=llm_client, tool_registry=default_registry)

    # COURSE path
    summary_course = agent.run_audit("₹18,000 AWS certification course")
    course_path = summary_course.findings[0].routing_path
    assert "✓ Category: COURSE" in course_path
    assert "→ Course Policy" in course_path
    assert "→ Approval required" in course_path
    assert "→ Checking Approval" in course_path
    assert "→ Receipt validation" in course_path
    assert "✓ Complete" in course_path

    # WFH path
    agent_wfh = ExpenseAuditAgent(llm_client=LLMClient(mock_mode=True), tool_registry=default_registry)
    summary_wfh = agent_wfh.run_audit("₹18,500 monitor for home office")
    wfh_path = summary_wfh.findings[0].routing_path
    assert "✓ Category: WFH_SETUP" in wfh_path
    assert "→ WFH Policy" in wfh_path
    assert "→ Monitor limit check" in wfh_path
    assert "⊘ Approval not required" in wfh_path
    assert "→ Receipt validation" in wfh_path
    assert "✓ Complete" in wfh_path
