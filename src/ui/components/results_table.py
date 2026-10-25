from typing import Any, Dict, List
import streamlit as st
import pandas as pd
from src.models import AuditSummary, AuditClassification, RiskLevel

CLASSIFICATION_BADGES = {
    AuditClassification.COMPLIANT: "🟢 COMPLIANT",
    AuditClassification.POLICY_EXCEPTION: "🔵 POLICY EXCEPTION",
    AuditClassification.MISSING_APPROVAL: "🔴 MISSING APPROVAL",
    AuditClassification.RECEIPT_MISMATCH: "🟠 RECEIPT MISMATCH",
    AuditClassification.MISSING_DOCUMENT: "📄 MISSING DOCUMENT",
    AuditClassification.REQUIRES_REVIEW: "⚠️ REQUIRES REVIEW",
}

def get_classification_badge(classification: Any) -> str:
    """Returns formatted badge string for classification enum."""
    if isinstance(classification, str):
        try:
            enum_val = AuditClassification(classification)
            return CLASSIFICATION_BADGES.get(enum_val, f"⚪ {classification}")
        except ValueError:
            return f"⚪ {classification}"
    return CLASSIFICATION_BADGES.get(classification, str(classification))


def render_results_table(summary: AuditSummary) -> None:
    """Renders line-item findings table with expandable evidence details."""
    st.subheader("📋 Expense Audit Findings Table")

    if not summary or not summary.findings:
        st.info("No audit findings to display.")
        return

    # Build summary dataframe for high-level table
    table_data = []
    for f in summary.findings:
        table_data.append({
            "Item ID": f.item_id,
            "Expense Type": getattr(f, "expense_type", None) or "N/A",
            "Classification": get_classification_badge(f.classification),
            "Approval Status": getattr(f, "approval_status", None) or "-",
            "Checks Performed": ", ".join(f.checks_performed) if getattr(f, "checks_performed", None) else "-",
            "Checks Skipped": ", ".join(f.checks_skipped) if getattr(f, "checks_skipped", None) else "-",
            "Variance / Excess": f"₹{f.calculated_variance:,.2f}" if f.calculated_variance > 0 else "-",
            "Risk Level": str(f.risk_level.value if hasattr(f.risk_level, 'value') else f.risk_level),
            "Action": f.action_recommended or "None"
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📝 Detailed Evidence & Finding Analysis")

    for idx, f in enumerate(summary.findings, 1):
        badge = get_classification_badge(f.classification)
        item_id = f.item_id
        exp_type = getattr(f, "expense_type", None) or "General"
        variance_str = f" (Excess Variance: ₹{f.calculated_variance:,.2f})" if f.calculated_variance > 0 else ""

        with st.expander(f"{idx}. Item [{item_id}] ({exp_type}) - {badge}{variance_str}", expanded=(f.calculated_variance > 0)):
            if getattr(f, "routing_path", None):
                st.markdown("**Selected Routing Path:**")
                st.code("\n".join(f.routing_path), language="text")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Expense Type:** `{exp_type}`")
                st.markdown(f"**Approval Status:** `{getattr(f, 'approval_status', None) or 'N/A'}`")
            with col2:
                st.markdown(f"**Checks Performed:** {', '.join(f.checks_performed) if getattr(f, 'checks_performed', None) else 'N/A'}")
                st.markdown(f"**Checks Skipped:** {', '.join(f.checks_skipped) if getattr(f, 'checks_skipped', None) else 'None'}")

            st.markdown(f"**Reasoning:** {f.reasoning}")
            
            if f.evidence:
                st.markdown("**Evidence Citations:**")
                for ev in f.evidence:
                    st.markdown(f"- {ev}")
            
            if f.action_recommended:
                st.markdown(f"**Recommended Action:** {f.action_recommended}")

