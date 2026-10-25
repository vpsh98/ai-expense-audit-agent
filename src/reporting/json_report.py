import json
from src.reporting.formatter import BaseReportGenerator
from src.models import AuditSummary, AuditClassification

class JSONReportGenerator(BaseReportGenerator):
    """Generates machine-readable JSON compliance report payloads."""

    def generate(self, summary: AuditSummary, indent: int = 2) -> str:
        total_variance = self.calculate_total_variance(summary)
        missing_approvals_count = sum(
            1 for f in summary.findings if f.classification == AuditClassification.MISSING_APPROVAL
        )

        payload = {
            "session_id": summary.session_id or "SESS-DEFAULT",
            "summary_metrics": {
                "total_items_audited": summary.total_items_audited,
                "total_claimed_amount": summary.total_claimed_amount,
                "total_compliant_amount": summary.total_compliant_amount,
                "total_excess_variance": round(total_variance, 2),
                "compliant_count": summary.compliant_count,
                "exception_count": summary.exception_count,
                "missing_approvals_count": missing_approvals_count,
            },
            "findings": [
                {
                    "finding_id": f.finding_id or f"FND-{f.item_id}",
                    "item_id": f.item_id,
                    "employee_id": f.employee_id,
                    "expense_type": getattr(f, "expense_type", None),
                    "classification": str(f.classification.value if hasattr(f.classification, 'value') else f.classification),
                    "approval_status": getattr(f, "approval_status", None),
                    "checks_performed": getattr(f, "checks_performed", []),
                    "checks_skipped": getattr(f, "checks_skipped", []),
                    "routing_path": getattr(f, "routing_path", []),
                    "reasoning": f.reasoning,
                    "calculated_variance": round(f.calculated_variance, 2),
                    "evidence": f.evidence,
                    "risk_level": str(f.risk_level.value if hasattr(f.risk_level, 'value') else f.risk_level),
                    "action_recommended": f.action_recommended,
                }
                for f in summary.findings
            ]
        }

        return json.dumps(payload, indent=indent, ensure_ascii=False)
