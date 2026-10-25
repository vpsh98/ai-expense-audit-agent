import sys
from pathlib import Path

# Ensure project root is in sys.path when launched directly via `streamlit run src/ui/app.py`
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import streamlit as st
from src.ui.components import (
    render_sidebar,
    render_activity_feed,
    render_summary_cards,
    render_results_table,
    render_report_view,
    render_presentation_view,
)
from src.agent import ExpenseAuditAgent

def main():
    st.set_page_config(
        page_title="AI Expense Audit Agent",
        page_icon="🧾",
        layout="wide"
    )

    # Initialize session state
    if "audit_summary" not in st.session_state:
        st.session_state["audit_summary"] = None
    if "execution_trace" not in st.session_state:
        st.session_state["execution_trace"] = []
    if "show_presentation" not in st.session_state:
        st.session_state["show_presentation"] = False

    header_col1, header_col2 = st.columns([3, 1.2])
    with header_col1:
        st.title("🛡️ AI Enterprise Expense Audit Agent")
        st.markdown(
            "Autonomous AI Agent powered by **Google ADK & Gemini** that audits enterprise expense claims "
            "against corporate policies, manager pre-approvals, and receipts with 100% financial accuracy."
        )
    with header_col2:
        st.write("")
        btn_label = "❌ Close PPT Deck" if st.session_state["show_presentation"] else "📽️ Architecture & Flow PPT"
        if st.button(btn_label, use_container_width=True, type="primary" if not st.session_state["show_presentation"] else "secondary"):
            st.session_state["show_presentation"] = not st.session_state["show_presentation"]
            st.rerun()

    st.markdown("---")

    # Embedded Presentation Slide Deck (Toggled by Button Click)
    if st.session_state["show_presentation"]:
        render_presentation_view(key_prefix="header_deck")
        st.markdown("---")

    # Render Sidebar
    sidebar_state = render_sidebar()

    # Handle Run Audit Button Click
    if sidebar_state["run_clicked"]:
        st.session_state["audit_summary"] = None
        st.session_state["execution_trace"] = []

        # If user uploaded a custom file in sidebar, write to expenses.csv for audit
        uploaded_df = sidebar_state.get("uploaded_df")
        if uploaded_df is not None and not uploaded_df.empty:
            try:
                from src.config import settings
                expenses_csv_path = settings.DATA_DIR / "expenses.csv"
                uploaded_df.to_csv(expenses_csv_path, index=False)
            except Exception as e:
                st.warning(f"⚠️ Could not write uploaded file to disk ({e}). Please close expenses.csv if opened in Excel.")

        audit_prompt = sidebar_state["audit_prompt"]
        selected_emp_name = sidebar_state.get("selected_employee_name")
        selected_emp_id = sidebar_state.get("selected_employee_id")
        use_adk = sidebar_state.get("use_adk", True)

        # Guarantee prompt reflects the selected employee
        if selected_emp_name:
            if selected_emp_name.lower() not in audit_prompt.lower() and (not selected_emp_id or selected_emp_id.lower() not in audit_prompt.lower()):
                audit_prompt = f"Audit {selected_emp_name}'s expenses."
        elif not selected_emp_name and "all" not in audit_prompt.lower():
            audit_prompt = "Audit all employee expense claims."

        with st.spinner("🤖 AI Agent is conducting expense audit..."):
            from src.agent.llm_client import LLMClient
            is_mock = sidebar_state.get("is_mock", False)
            is_react = sidebar_state.get("is_react", False)

            if is_mock:
                llm_client = LLMClient(mock_mode=True)
                agent = ExpenseAuditAgent(llm_client=llm_client)
                summary = agent.adk_orchestrator.orchestrate_audit(audit_prompt, agent.steps, mock_mode=True)
            elif is_react:
                llm_client = LLMClient(mock_mode=False)
                agent = ExpenseAuditAgent(llm_client=llm_client)
                summary = agent.run_audit(audit_prompt)
            else:
                # Live Google ADK Multi-Agent Orchestration with Gemini LLM
                llm_client = LLMClient(mock_mode=False)
                agent = ExpenseAuditAgent(llm_client=llm_client)
                summary = agent.adk_orchestrator.orchestrate_audit(audit_prompt, agent.steps, mock_mode=False)

            st.session_state["audit_summary"] = summary
            st.session_state["execution_trace"] = agent.get_execution_trace()

        st.toast("Audit completed successfully!", icon="✅")

    # Main Dashboard Area
    summary = st.session_state["audit_summary"]
    execution_trace = st.session_state["execution_trace"]

    if summary is not None:
        # Render Executive KPI Metric Cards
        render_summary_cards(summary)
        st.markdown("---")

    # Layout: Split Activity Feed and Audit Results Tabs
    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        render_activity_feed(execution_trace, summary=summary)

    with col_right:
        if summary is None:
            st.subheader("📊 Audit Execution & Results")
            st.info("Select employee and click '🚀 Run AI Audit' in sidebar to run the audit.")
            with st.expander("📽️ System Overview: Architecture & Multi-Agent Flow Slides", expanded=False):
                render_presentation_view(key_prefix="expander_deck")
        else:
            tab_results, tab_reports, tab_ppt = st.tabs([
                "📋 Line-Item Audit Findings",
                "📄 Executive Reports & Exports",
                "📽️ Architecture & Flow PPT",
            ])
            
            with tab_results:
                render_results_table(summary)

            with tab_reports:
                render_report_view(summary)

            with tab_ppt:
                render_presentation_view(key_prefix="tab_deck")

if __name__ == "__main__":
    main()
