import streamlit as st
import streamlit.components.v1 as components
from src.models import AuditSummary
from src.reporting import (
    MarkdownReportGenerator,
    JSONReportGenerator,
    HTMLPDFReportGenerator,
)

def render_report_view(summary: AuditSummary) -> None:
    """Renders formatted audit report previews with one-click download buttons."""
    st.subheader("📄 Executive Audit Report & Data Export")

    if not summary:
        st.info("No audit report available. Run an audit to generate reports.")
        return

    md_report = MarkdownReportGenerator().generate(summary)
    json_report = JSONReportGenerator().generate(summary)
    html_report = HTMLPDFReportGenerator().generate(summary)

    # Download Buttons Row
    dl_col1, dl_col2, dl_col3 = st.columns(3)

    session_id = summary.session_id or "audit_report"
    
    with dl_col1:
        st.download_button(
            label="📥 Download Markdown (.md)",
            data=md_report,
            file_name=f"{session_id}.md",
            mime="text/markdown",
            use_container_width=True
        )

    with dl_col2:
        st.download_button(
            label="📥 Download JSON (.json)",
            data=json_report,
            file_name=f"{session_id}.json",
            mime="application/json",
            use_container_width=True
        )

    with dl_col3:
        st.download_button(
            label="📥 Download HTML (.html)",
            data=html_report,
            file_name=f"{session_id}.html",
            mime="text/html",
            use_container_width=True
        )

    st.markdown("---")

    # Preview Tabs
    tab_md, tab_html, tab_json = st.tabs(["📝 Markdown Preview", "🎨 Executive HTML View", "💻 JSON Payload"])

    with tab_md:
        st.markdown(md_report)

    with tab_html:
        components.html(html_report, height=600, scrolling=True)

    with tab_json:
        st.code(json_report, language="json")
