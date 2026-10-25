from typing import Any, Dict, Optional
import streamlit as st
import pandas as pd
from src.data import EmployeeRepository
from src.config import settings

def render_sidebar(employee_repo: Optional[EmployeeRepository] = None) -> Dict[str, Any]:
    """Renders the Streamlit sidebar for expense file uploads, employee selection, and audit prompts."""
    st.sidebar.title("🤖 AI Expense Audit Agent")
    st.sidebar.markdown("---")

    # Environment / LLM Mode indicator & Engine Selector
    st.sidebar.subheader("⚙️ System Status")
    mode_selection = st.sidebar.radio(
        "Agent Orchestration Engine:",
        [
            "⚡ Google ADK Multi-Agent (Live Gemini)",
            "✨ Single-Agent ReAct (Live Gemini)",
            "🧪 Deterministic Mock (Offline/Fast)",
        ],
        index=0,
        help="Google ADK uses multi-agent triage and specialists (CourseAgent, WfhAgent, TravelAgent, SoftwareAgent) with real Gemini LLM calls. Single-Agent ReAct uses standard single-agent loop. Deterministic Mock runs offline without LLM."
    )
    is_live_adk = ("Google ADK" in mode_selection)
    is_mock = ("Deterministic Mock" in mode_selection)
    is_react = ("Single-Agent ReAct" in mode_selection)
    st.sidebar.caption(f"**Model:** `{settings.LLM_MODEL}`")
    st.sidebar.markdown("---")

    # Employee Selector
    st.sidebar.subheader("👤 Select Employee")
    repo = employee_repo or EmployeeRepository()
    employees = repo.get_all()

    emp_options = ["None / All"] + [f"{emp.get('name')} ({emp.get('employee_id')})" for emp in employees]
    default_idx = 1 if len(emp_options) > 1 else 0
    selected_emp_str = st.sidebar.selectbox("Choose employee to audit:", emp_options, index=default_idx, key="emp_select_box")

    selected_emp_id = None
    selected_emp_name = None
    if selected_emp_str != "None / All":
        # Extract name and ID from string format "Name (EMP001)"
        parts = selected_emp_str.rsplit(" (", 1)
        selected_emp_name = parts[0]
        selected_emp_id = parts[1].rstrip(")") if len(parts) > 1 else None

    # Expense File Uploader
    st.sidebar.subheader("📁 Upload Expense File")
    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV or Excel file:",
        type=["csv", "xlsx"],
        help="Supports .csv or .xlsx containing expense line items."
    )

    uploaded_df = None
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file)
            st.sidebar.success(f"Uploaded {len(uploaded_df)} expense items from {uploaded_file.name}")
        except Exception as e:
            st.sidebar.error(f"Error reading uploaded file: {e}")

    # Audit Request Prompt Box
    st.sidebar.subheader("💬 Audit Request Prompt")

    # Compute appropriate default prompt for selected employee
    if selected_emp_name:
        default_prompt = f"Audit {selected_emp_name}'s expenses."
    else:
        default_prompt = "Audit all employee expense claims."

    # Synchronize session state so changing dropdown always updates the text area
    if "sidebar_selected_emp" not in st.session_state:
        st.session_state["sidebar_selected_emp"] = selected_emp_str
        st.session_state["sidebar_prompt_val"] = default_prompt
    elif st.session_state["sidebar_selected_emp"] != selected_emp_str:
        st.session_state["sidebar_selected_emp"] = selected_emp_str
        st.session_state["sidebar_prompt_val"] = default_prompt

    user_prompt = st.sidebar.text_area(
        "Natural language audit query:",
        key="sidebar_prompt_val",
        height=100
    )

    run_clicked = st.sidebar.button("🚀 Run AI Audit", type="primary", use_container_width=True)

    return {
        "selected_employee_id": selected_emp_id,
        "selected_employee_name": selected_emp_name,
        "uploaded_file": uploaded_file,
        "uploaded_df": uploaded_df,
        "audit_prompt": user_prompt,
        "run_clicked": run_clicked,
        "is_live_adk": is_live_adk,
        "is_mock": is_mock,
        "is_react": is_react,
        "use_adk": is_live_adk or is_mock,
    }
