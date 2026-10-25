from typing import List
from src.reporting.formatter import BaseReportGenerator
from src.models import AuditSummary, AuditClassification

class MarkdownReportGenerator(BaseReportGenerator):
    """Generates executive audit documentation in GitHub-Flavored Markdown."""

    def generate(self, summary: AuditSummary) -> str:
        total_variance = self.calculate_total_variance(summary)
        missing_approvals_count = sum(
            1 for f in summary.findings if f.classification == AuditClassification.MISSING_APPROVAL
        )

        lines = [
            "# 📋 AI Expense Audit Executive Report",
            "",
            f"**Session ID:** `{summary.session_id or 'SESS-DEFAULT'}`",
            "",
            "## 📊 Executive Summary & Key Metrics",
            "",
            "| Metric | Value |",
            "| :--- | :--- |",
            f"| **Total Line Items Audited** | `{summary.total_items_audited}` |",
            f"| **Total Claimed Amount** | `{self.format_currency(summary.total_claimed_amount)}` |",
            f"| **Total Compliant Amount** | `{self.format_currency(summary.total_compliant_amount)}` |",
            f"| **Total Excess / Variance** | `{self.format_currency(total_variance)}` |",
            f"| **Compliant Items Count** | `{summary.compliant_count}` |",
            f"| **Policy Exception Count** | `{summary.exception_count}` |",
            f"| **Missing Approvals Count** | `{missing_approvals_count}` |",
            "",
            "---",
            "",
            "## 🔍 Audit Findings Overview",
            "",
            "| Item ID | Classification | Variance | Risk Level | Recommended Action |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]

        for finding in summary.findings:
            item_id = finding.item_id
            classification_str = str(finding.classification.value if hasattr(finding.classification, 'value') else finding.classification)
            variance_str = self.format_currency(finding.calculated_variance) if finding.calculated_variance > 0 else "-"
            risk_str = str(finding.risk_level.value if hasattr(finding.risk_level, 'value') else finding.risk_level)
            action = finding.action_recommended or "None"

            lines.append(
                f"| `{item_id}` | `{classification_str}` | `{variance_str}` | `{risk_str}` | {action} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 📝 Detailed Finding Analysis & Evidence Citations",
            ""
        ])

        if not summary.findings:
            lines.append(" *No audit findings recorded.*")
        else:
            for idx, finding in enumerate(summary.findings, 1):
                classification_str = str(finding.classification.value if hasattr(finding.classification, 'value') else finding.classification)
                risk_str = str(finding.risk_level.value if hasattr(finding.risk_level, 'value') else finding.risk_level)
                variance_str = self.format_currency(finding.calculated_variance)

                lines.extend([
                    f"### {idx}. Finding `{finding.finding_id or f'FND-{finding.item_id}'}` - Item `{finding.item_id}`",
                    f"- **Classification:** `{classification_str}`",
                    f"- **Expense Type:** `{getattr(finding, 'expense_type', 'N/A') or 'N/A'}`",
                    f"- **Approval Status:** `{getattr(finding, 'approval_status', 'N/A') or 'N/A'}`",
                    f"- **Risk Level:** `{risk_str}`",
                    f"- **Calculated Variance:** {variance_str}",
                    f"- **Reasoning:** {finding.reasoning}",
                ])

                if getattr(finding, "checks_performed", None):
                    lines.append(f"- **Checks Performed:** {', '.join(finding.checks_performed)}")
                if getattr(finding, "checks_skipped", None):
                    lines.append(f"- **Checks Skipped:** {', '.join(finding.checks_skipped)}")

                if finding.evidence:
                    lines.append("- **Evidence Citations:**")
                    for ev in finding.evidence:
                        lines.append(f"  * {ev}")

                if finding.action_recommended:
                    lines.append(f"- **Recommended Action:** {finding.action_recommended}")

                lines.append("")

        return "\n".join(lines)
