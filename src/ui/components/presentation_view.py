"""Interactive presentation slide viewer and PowerPoint downloader component for Streamlit."""
from typing import Any, Dict, List
import streamlit as st
from src.reporting.presentation_generator import (
    SLIDE_DATA,
    generate_presentation_bytes,
)


def render_presentation_view(key_prefix: str = "main") -> None:
    """Renders the interactive presentation slide deck inside the Streamlit UI."""
    st.markdown("### 📽️ Architecture, Multi-Agent Flow & Tech Stack Presentation")
    st.markdown(
        "Executive presentation detailing the **Google ADK multi-agent architecture**, "
        "decision routing flows, zero-hallucination guardrails, and enterprise tech stack."
    )

    # Initialize current slide in session state
    if "current_slide_idx" not in st.session_state:
        st.session_state["current_slide_idx"] = 0

    total_slides = len(SLIDE_DATA)
    curr_idx = st.session_state["current_slide_idx"]
    slide_titles = [f"Slide {s['slide_number']}: {s['category']}" for s in SLIDE_DATA]

    # Top Control Toolbar: Navigation + PPTX Download
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1.2, 1.2, 2.5, 2.0])

    with ctrl_col1:
        if st.button("⬅️ Previous", disabled=(curr_idx == 0), key=f"{key_prefix}_btn_prev_slide", use_container_width=True):
            new_idx = max(0, curr_idx - 1)
            st.session_state["current_slide_idx"] = new_idx
            select_key = f"{key_prefix}_select_slide_jump"
            if select_key in st.session_state:
                st.session_state[select_key] = slide_titles[new_idx]
            st.rerun()

    with ctrl_col2:
        if st.button("Next ➡️", disabled=(curr_idx == total_slides - 1), key=f"{key_prefix}_btn_next_slide", use_container_width=True):
            new_idx = min(total_slides - 1, curr_idx + 1)
            st.session_state["current_slide_idx"] = new_idx
            select_key = f"{key_prefix}_select_slide_jump"
            if select_key in st.session_state:
                st.session_state[select_key] = slide_titles[new_idx]
            st.rerun()

    with ctrl_col3:
        select_key = f"{key_prefix}_select_slide_jump"
        if select_key in st.session_state:
            curr_str = st.session_state[select_key]
            if curr_str in slide_titles and slide_titles.index(curr_str) != curr_idx:
                st.session_state[select_key] = slide_titles[curr_idx]

        selected_slide_str = st.selectbox(
            "Jump to Slide",
            options=slide_titles,
            index=curr_idx,
            label_visibility="collapsed",
            key=select_key
        )
        selected_idx = slide_titles.index(selected_slide_str)
        if selected_idx != curr_idx:
            st.session_state["current_slide_idx"] = selected_idx
            st.rerun()

    with ctrl_col4:
        pptx_bytes = generate_presentation_bytes()
        st.download_button(
            label="📥 Download .pptx File",
            data=pptx_bytes,
            file_name="AI_Expense_Audit_Agent_Architecture.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True,
            key=f"{key_prefix}_btn_download_pptx"
        )

    st.markdown("---")

    # Render Current Slide
    slide = SLIDE_DATA[curr_idx]

    # Slide Container Card Styling
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                    padding: 24px 30px; border-radius: 12px; margin-bottom: 20px;
                    border: 1px solid #334155; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="background: #2563eb; color: #ffffff; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                    {slide['category']}
                </span>
                <span style="color: #94a3b8; font-size: 13px; font-weight: 500;">
                    Slide {slide['slide_number']} of {total_slides}
                </span>
            </div>
            <h2 style="color: #f8fafc; margin: 0 0 6px 0; font-size: 26px; font-weight: 700;">
                {slide['title']}
            </h2>
            <p style="color: #38bdf8; margin: 0; font-size: 14px; font-weight: 400;">
                {slide['subtitle']}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Slide Body Layout: Content vs Sidebar Highlights
    body_col_left, body_col_right = st.columns([1.8, 1.2])

    with body_col_left:
        st.markdown("#### 📌 Key Architecture & Flow Points")
        for point in slide["bullet_points"]:
            st.markdown(f"- {point}")

        # Render Slide-Specific Visual Diagram
        if slide["slide_number"] == 3:
            # Architecture Diagram
            st.markdown("##### 🏛️ Google ADK Multi-Agent Architecture")
            st.code(
                """
+---------------------------------------------------------------------------------+
|                                Streamlit Web UI                                 |
|            (KPI Cards, Live Activity Feed, Findings Table, PPTX Viewer)         |
+----------------------------------------+----------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                Google ADK Root Orchestrator (gemini-3.5-flash-lite)             |
|                              ExpenseRootOrchestrator                            |
+----------------------------------------+----------------------------------------+
                                         |
                 ADK transfer_to_agent() | Autonomous Routing
                                         v
     +--------------------+--------------------+--------------------+
     |                    |                    |                    |
     v                    v                    v                    v
+--------------+   +---------------+   +---------------+   +-------------------+
| CourseAgent  |   | WfhSetupAgent |   |  TravelAgent  |   | SoftwareLicAgent  |
| (Education)  |   | (Equipment)   |   | (Flight/Hotel)|   | (SaaS/Tooling)    |
+-------+------+   +-------+-------+   +-------+-------+   +---------+---------+
        |                  |                   |                     |
        +------------------+---------+---------+---------------------+
                                     | Dynamic Tool Invocations
                                     v
+---------------------------------------------------------------------------------+
|                      Deterministic Tools & Data Repositories                    |
|      [search_policy]    [check_approval]    [calculate]    [read_receipt]       |
+---------------------------------------------------------------------------------+
                """,
                language="text"
            )

        elif slide["slide_number"] == 4:
            # Multi-Agent Execution Flow
            st.markdown("##### 🔀 Real Multi-Turn Google ADK Execution Flow")
            st.code(
                """
User Claim
    │
    ▼
[Turn 1] ExpenseRootOrchestrator (Gemini LLM)
    │
    ├──▶ Evaluates claim context & calls transfer_to_agent(agent_name=...)
    │
    ├─────────────────────────────────┬─────────────────────────────────┐
    ▼                                 ▼                                 ▼
CourseAgent (5 LLM Turns)       WfhSetupAgent (4 LLM Turns)      Travel / Software
    │                                 │                                 │
[Turn 2] search_expense_policy  [Turn 2] search_expense_policy   [Turn 2] search_policy
    │                                 │                                 │
[Turn 3] check_approval         [Turn 3] read_receipt            [Turn 3] check_approval
  (Only if amount > ₹10k)         (Approval skipped by default)    (If over limit)
    │                                 │                                 │
[Turn 4] read_receipt           [Turn 4] Synthesis Report        [Turn 4] read_receipt
    │                                                                   │
[Turn 5] Synthesis Report                                        [Turn 5] Synthesis
    │                                 │                                 │
    └─────────────────────────────────┴─────────────────────────────────┘
                                      │
                                      ▼
                        Structured AuditSummary & UI Trace
                """,
                language="text"
            )

        elif slide["slide_number"] == 5:
            # Policy Decision Table
            st.markdown("##### ⚖️ Policy Decision Matrix")
            st.table([
                {"Category": "COURSE", "Policy Limit": "₹25,000", "Approval Rule": "Mandatory > ₹10,000", "Default Action": "Skip approval if <= ₹10k"},
                {"Category": "WFH_SETUP", "Policy Limit": "Monitor ₹15k, etc.", "Approval Rule": "Not required by default", "Default Action": "Calculate variance via tool"},
                {"Category": "TRAVEL", "Policy Limit": "Flight ₹25k, Hotel ₹8k", "Approval Rule": "Required if over limit", "Default Action": "Verify pre-approval"},
                {"Category": "SOFTWARE", "Policy Limit": "₹10,000", "Approval Rule": "Mandatory > ₹5,000", "Default Action": "Check developer tooling approval"},
                {"Category": "UNKNOWN", "Policy Limit": "N/A", "Approval Rule": "N/A", "Default Action": "Flag as REQUIRES_REVIEW"},
            ])

        elif slide["slide_number"] == 6:
            # Tech Stack Grid
            st.markdown("##### 🛠️ Core Technology Components")
            tech_c1, tech_c2, tech_c3 = st.columns(3)
            with tech_c1:
                st.info("**Google ADK 2.10**\nMulti-agent orchestration")
                st.info("**Pydantic 2.13**\nStrict schema validation")
            with tech_c2:
                st.info("**Google Gemini 3.5**\nFlash Lite Tool-calling LLM")
                st.info("**Python-PPTX 1.0**\nExecutive slide deck export")
            with tech_c3:
                st.info("**Streamlit 1.64**\nReal-time audit dashboard")
                st.info("**PyTest 9.1**\n82 automated tests passing")

    with body_col_right:
        st.markdown("#### ⚡ Slide Highlights")
        for label, val in slide.get("highlights", []):
            st.markdown(
                f"""
                <div style="background: #f8fafc; border-left: 4px solid #2563eb;
                            padding: 10px 14px; border-radius: 4px; margin-bottom: 10px;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div style="color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase;">
                        {label}
                    </div>
                    <div style="color: #0f172a; font-size: 14px; font-weight: 600; margin-top: 2px;">
                        {val}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("---")
        st.markdown("**Slide Quick Index:**")
        for i, s in enumerate(SLIDE_DATA):
            is_active = (i == curr_idx)
            btn_label = f"{'👉 ' if is_active else ''}Slide {s['slide_number']}: {s['category']}"
            if st.button(btn_label, key=f"{key_prefix}_quick_idx_slide_{i}", use_container_width=True):
                st.session_state["current_slide_idx"] = i
                select_key = f"{key_prefix}_select_slide_jump"
                if select_key in st.session_state:
                    st.session_state[select_key] = slide_titles[i]
                st.rerun()
