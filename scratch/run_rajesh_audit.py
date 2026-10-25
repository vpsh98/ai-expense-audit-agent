import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.agent import ExpenseAuditAgent
from src.reporting import MarkdownReportGenerator

agent = ExpenseAuditAgent()
summary = agent.audit_employee_expenses("EMP001", "2026-09")

print("=== AUDIT SUMMARY ===")
print(f"Session ID: {summary.session_id}")
print(f"Total Items Audited: {summary.total_items_audited}")
print(f"Compliant Count: {summary.compliant_count}")
print(f"Exception Count: {summary.exception_count}")
print(f"Total Amount Claimed: Rs. {summary.total_claimed_amount:,.2f}")
print(f"Total Compliant Amount: Rs. {summary.total_compliant_amount:,.2f}")
print(f"Total Non-Compliant Amount: Rs. {summary.total_claimed_amount - summary.total_compliant_amount:,.2f}")
print("\n=== FINDINGS ===")
for f in summary.findings:
    print(f"• Item ID: {f.item_id} | Employee ID: {f.employee_id}")
    print(f"  Classification: {f.classification}")
    print(f"  Risk Level: {f.risk_level}")
    print(f"  Calculated Variance: Rs. {f.calculated_variance:,.2f}")
    print(f"  Reasoning: {f.reasoning}")
    print(f"  Evidence: {f.evidence}")
    print(f"  Action Recommended: {f.action_recommended}")
    print("-" * 60)

md_report = MarkdownReportGenerator().generate(summary)
print("\n=== MARKDOWN REPORT ===")
print(md_report)
