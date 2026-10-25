import streamlit as st
from src.models import AuditSummary
from src.reporting.formatter import BaseReportGenerator

def render_summary_cards(summary: AuditSummary) -> None:
    """Renders executive KPI metric cards for audit overview and LLM telemetry."""
    if not summary:
        return

    total_claimed = summary.total_claimed_amount
    total_compliant = summary.total_compliant_amount
    total_variance = BaseReportGenerator.calculate_total_variance(summary)
    exceptions_count = summary.exception_count

    # Row 1: Financial & Policy Audit Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Claimed",
            value=f"₹{total_claimed:,.2f}",
            help="Total monetary amount claimed across all audited expense line items."
        )

    with col2:
        st.metric(
            label="Total Compliant",
            value=f"₹{total_compliant:,.2f}",
            help="Monetary amount verified as compliant with company policies and pre-approvals."
        )

    with col3:
        st.metric(
            label="Total Discrepancy",
            value=f"₹{total_variance:,.2f}",
            delta=f"-₹{total_variance:,.2f}" if total_variance > 0 else "₹0.00",
            delta_color="inverse",
            help="Total excess monetary amount exceeding policy limits without prior approval."
        )

    with col4:
        st.metric(
            label="Policy Exceptions",
            value=f"{exceptions_count} items",
            delta=f"{exceptions_count} flagged" if exceptions_count > 0 else "Clean",
            delta_color="inverse",
            help="Count of line items flagged with policy exceptions, missing approvals, or document errors."
        )

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    # Row 2: Real Google ADK & Gemini Token Usage & Cost Telemetry
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)

    with col_t1:
        total_tokens = getattr(summary, "total_tokens", 0) or 0
        prompt_tokens = getattr(summary, "prompt_tokens", 0) or 0
        completion_tokens = getattr(summary, "completion_tokens", 0) or 0
        st.metric(
            label="⚡ Total Token Usage",
            value=f"{total_tokens:,}" if total_tokens > 0 else "0",
            delta=f"Prompt: {prompt_tokens:,} | Output: {completion_tokens:,}" if total_tokens > 0 else "Rule-based (0 tokens)",
            delta_color="off",
            help="Cumulative prompt tokens and generated response tokens across all ADK agent reasoning steps."
        )

    with col_t2:
        cost_inr = getattr(summary, "estimated_cost_inr", 0.0) or 0.0
        cost_usd = getattr(summary, "estimated_cost_usd", 0.0) or 0.0
        st.metric(
            label="💵 Est. Inference Cost",
            value=f"₹{cost_inr:.4f}" if cost_inr > 0 else "₹0.00",
            delta=f"${cost_usd:.6f} USD" if cost_usd > 0 else "$0.00 USD",
            delta_color="off",
            help="Estimated Gemini API cost based on official input/output token pricing ($0.075 / $0.30 per 1M tokens)."
        )

    with col_t3:
        llm_turns = getattr(summary, "llm_turns_count", 0) or 0
        st.metric(
            label="🤖 LLM Inference Turns",
            value=f"{llm_turns} turns" if llm_turns > 0 else "0 (Mock)",
            delta="Live Multi-Agent Handoffs" if llm_turns > 0 else "Offline Mode",
            delta_color="off",
            help="Number of back-and-forth LLM inference turns between Root and Specialist ADK agents."
        )

    with col_t4:
        st.metric(
            label="🧠 Multi-Agent Stack",
            value="Google ADK",
            delta="gemini-3.5-flash-lite" if total_tokens > 0 else "Deterministic Fallback",
            delta_color="off",
            help="Google Agent Development Kit runtime backed by Gemini 3.5 Flash Lite with deterministic tools."
        )
