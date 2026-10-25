from typing import Dict, List, Any, Optional
import streamlit as st
from src.models import AgentStep, ToolResult

def format_agent_step_title(step: AgentStep) -> str:
    """Formats an AgentStep into a clean, human-readable activity title."""
    action = step.action
    args = step.action_input or {}
    obs = step.observation

    if action == "get_employee_details":
        query = args.get("employee_name") or args.get("employee_id") or "employee"
        return f"🔍 Looking up profile for employee '{query}'..."

    elif action == "read_expense_report":
        emp_id = args.get("employee_id", "employee")
        period = args.get("period", "")
        return f"📄 Fetching expense line items for '{emp_id}' {f'({period})' if period else ''}..."

    elif action == "search_expense_policy":
        cat = args.get("category", "expense category")
        return f"📜 Querying spending policy limits for '{cat}'..."

    elif action == "calculate":
        op = args.get("operation", "compute")
        a = args.get("a", 0)
        b = args.get("b", 0)
        res_val = ""
        if isinstance(obs, ToolResult) and obs.success and isinstance(obs.result, dict):
            res_val = f" = ₹{obs.result.get('value'):,.2f}" if "value" in obs.result else ""
        return f"🧮 Calculating {op}: {a} vs {b}{res_val}"

    elif action == "check_approval":
        cat = args.get("category", "")
        amt = args.get("amount", 0)
        return f"🛡️ Verifying manager pre-approval status for {cat} (₹{amt:,.2f})..."

    elif action == "read_receipt":
        rcp_query = args.get("expense_id") or args.get("receipt_id") or "receipt"
        return f"🧾 Inspecting digital receipt invoice for '{rcp_query}'..."

    elif action == "transfer_to_agent":
        target = args.get("agent_name") or args.get("specialist") or "Specialist"
        return f"🔀 Root Agent → {target} (ADK Sub-Agent Transfer)"

    elif action in ("route_to_specialist", "delegate_specialist"):
        target = args.get("specialist") or args.get("agent_name") or "Specialist"
        return f"🔀 ADK Dispatch: Routed to {target}..."

    elif action in ("root_agent", "adk_root", "orchestrator"):
        return f"🎯 ADK Root Orchestrator: {step.thought or 'Coordinating expense audit'}"

    elif action:
        return f"⚙️ Executing action '{action}'..."

    if step.thought and "✓ Root Agent received" in step.thought:
        return "✓ Root Agent received request"

    return f"💡 Turn {step.step_number}: Reasoning & synthesis"


def render_activity_feed(steps: List[AgentStep], summary: Optional[Any] = None) -> None:
    """Renders the real-time agent activity feed and selected routing paths in Streamlit."""
    st.subheader("⚡ Agent Real-Time Activity Feed")

    if not steps:
        st.info("No active agent audit trace. Click '🚀 Run AI Audit' to begin.")
        return

    # Render selected branching routing paths cleanly without exposing raw chain-of-thought
    routing_paths_found = []
    if summary and hasattr(summary, "findings"):
        for f in summary.findings:
            if getattr(f, "routing_path", None):
                routing_paths_found.append((f.item_id, getattr(f, "expense_type", None) or "General", f.routing_path))

    if routing_paths_found:
        st.markdown("#### 🤖 Google ADK Multi-Agent Orchestration Flow")
        for item_id, exp_type, r_path in routing_paths_found:
            st.markdown(f"**Item [{item_id}] — `{exp_type}` Audit Path:**")
            path_display = "\n".join(r_path)
            st.code(path_display, language="text")
        st.markdown("---")

    for idx, step in enumerate(steps, 1):
        title = format_agent_step_title(step)
        with st.expander(f"Step {step.step_number}: {title}", expanded=(idx == len(steps))):
            clean_thought = step.thought or ""
            if "thought_signature" in clean_thought:
                clean_thought = clean_thought.split("thought_signature")[0].strip()
            if clean_thought:
                st.markdown(f"**Thought:** {clean_thought}")

            if step.action:
                st.markdown(f"**Action Tool:** `{step.action}`")
                if step.action_input:
                    st.json(step.action_input)

            if step.observation:
                st.markdown("**Observation Outcome:**")
                if isinstance(step.observation, ToolResult):
                    if step.observation.success:
                        st.success(step.observation.formatted_result or str(step.observation.result))
                    else:
                        st.error(f"Tool Error: {step.observation.error}")
                else:
                    st.info(str(step.observation))

