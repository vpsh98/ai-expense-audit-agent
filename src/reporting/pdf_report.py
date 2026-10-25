from src.reporting.formatter import BaseReportGenerator
from src.models import AuditSummary, AuditClassification

class HTMLPDFReportGenerator(BaseReportGenerator):
    """Generates clean HTML/PDF executive audit presentation reports."""

    def generate(self, summary: AuditSummary) -> str:
        total_variance = self.calculate_total_variance(summary)
        missing_approvals_count = sum(
            1 for f in summary.findings if f.classification == AuditClassification.MISSING_APPROVAL
        )

        findings_rows = []
        for finding in summary.findings:
            item_id = finding.item_id
            class_val = str(finding.classification.value if hasattr(finding.classification, 'value') else finding.classification)
            risk_val = str(finding.risk_level.value if hasattr(finding.risk_level, 'value') else finding.risk_level)
            var_fmt = self.format_currency(finding.calculated_variance) if finding.calculated_variance > 0 else "-"
            action = finding.action_recommended or "None"

            risk_class = "badge-low"
            if risk_val.upper() in ("HIGH", "CRITICAL"):
                risk_class = "badge-high"
            elif risk_val.upper() == "MEDIUM":
                risk_class = "badge-medium"

            findings_rows.append(f"""
            <tr>
                <td><strong>{item_id}</strong></td>
                <td><span class="badge">{class_val}</span></td>
                <td>{var_fmt}</td>
                <td><span class="badge {risk_class}">{risk_val}</span></td>
                <td>{action}</td>
            </tr>
            """)

        detailed_blocks = []
        for idx, finding in enumerate(summary.findings, 1):
            class_val = str(finding.classification.value if hasattr(finding.classification, 'value') else finding.classification)
            risk_val = str(finding.risk_level.value if hasattr(finding.risk_level, 'value') else finding.risk_level)
            var_fmt = self.format_currency(finding.calculated_variance)

            evidence_items = "".join([f"<li>{ev}</li>" for ev in finding.evidence])
            evidence_html = f"<ul>{evidence_items}</ul>" if finding.evidence else "<em>None</em>"

            detailed_blocks.append(f"""
            <div class="finding-card">
                <h3>{idx}. Finding {finding.finding_id or f'FND-{finding.item_id}'} (Item: {finding.item_id})</h3>
                <p><strong>Classification:</strong> <span class="badge">{class_val}</span> | 
                   <strong>Risk Level:</strong> <span class="badge">{risk_val}</span> | 
                   <strong>Variance:</strong> {var_fmt}</p>
                <p><strong>Reasoning:</strong> {finding.reasoning}</p>
                <p><strong>Evidence Citations:</strong></p>
                {evidence_html}
                <p><strong>Recommended Action:</strong> {finding.action_recommended or 'N/A'}</p>
            </div>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Expense Audit Executive Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 30px;
            background-color: #f8fafc;
            color: #1e293b;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #ffffff;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        h1 {{
            color: #0f172a;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 12px;
            margin-top: 0;
        }}
        h2 {{
            color: #1e293b;
            margin-top: 30px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f1f5f9;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-label {{
            font-size: 0.85rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .metric-value {{
            font-size: 1.4rem;
            font-weight: 700;
            color: #0f172a;
            margin-top: 6px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background-color: #f8fafc;
            color: #475569;
            font-weight: 600;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            background: #e2e8f0;
            color: #334155;
        }}
        .badge-low {{ background: #dcfce7; color: #166534; }}
        .badge-medium {{ background: #fef9c3; color: #854d0e; }}
        .badge-high {{ background: #fee2e2; color: #991b1b; }}
        .finding-card {{
            background: #f8fafc;
            border-left: 4px solid #3b82f6;
            padding: 16px 20px;
            margin-bottom: 16px;
            border-radius: 0 8px 8px 0;
        }}
        .finding-card h3 {{
            margin-top: 0;
            color: #1e293b;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 Expense Audit Executive Report</h1>
        <p><strong>Session ID:</strong> {summary.session_id or 'SESS-DEFAULT'}</p>
        
        <h2>📊 Financial Overview</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Items Audited</div>
                <div class="metric-value">{summary.total_items_audited}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Claimed</div>
                <div class="metric-value">{self.format_currency(summary.total_claimed_amount)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Compliant</div>
                <div class="metric-value">{self.format_currency(summary.total_compliant_amount)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Excess Variance</div>
                <div class="metric-value" style="color: #ef4444;">{self.format_currency(total_variance)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Exceptions Count</div>
                <div class="metric-value">{summary.exception_count}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Missing Approvals</div>
                <div class="metric-value">{missing_approvals_count}</div>
            </div>
        </div>

        <h2>🔍 Audit Findings Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Item ID</th>
                    <th>Classification</th>
                    <th>Variance</th>
                    <th>Risk</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {"".join(findings_rows)}
            </tbody>
        </table>

        <h2>📝 Detailed Finding Analysis & Evidence</h2>
        {"".join(detailed_blocks) if detailed_blocks else "<p><em>No detailed findings recorded.</em></p>"}
    </div>
</body>
</html>
"""
        return html_content
