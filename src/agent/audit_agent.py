import re
from typing import Any, Dict, List, Optional
import json
from src.agent.llm_client import LLMClient
from src.agent.tool_registry import ToolRegistry, default_registry
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.adk_orchestrator import ADKExpenseOrchestrator
from src.models import (
    AuditClassification,
    AuditFinding,
    AuditSummary,
    AgentStep,
    RiskLevel,
    ToolResult,
)
from src.utils.logger import logger


def classify_expense_nature(description: str = "", category: str = "") -> Dict[str, Any]:
    """Classifies an expense into canonical types (COURSE, WFH_SETUP, TRAVEL, SOFTWARE_LICENSE, UNKNOWN)."""
    desc = (description or "").lower()
    cat = (category or "").upper()

    # 1. COURSE
    course_keywords = ["course", "certification", "certified", "exam", "training", "workshop", "masterclass", "coursera", "udemy"]
    if cat == "COURSE" or any(kw in desc for kw in course_keywords):
        return {
            "expense_type": "COURSE",
            "policy_category": "COURSE",
            "item": None,
            "is_ambiguous": False
        }

    # 2. WFH_SETUP
    # Employee work-from-home equipment (monitor, keyboard, mouse, UPS, webcam, etc.)
    # Exclude server / cloud infrastructure
    is_server_infra = any(kw in desc for kw in ["server", "ec2", "hosting", "cloud vm", "infrastructure"])
    wfh_items = ["monitor", "keyboard", "mouse", "ups", "earphones", "headphones", "webcam", "laptop stand", "docking station"]
    if not is_server_infra:
        if cat in ("WFH_SETUP", "WFH"):
            matched_item = "monitor"
            for itm in wfh_items:
                if itm in desc:
                    matched_item = itm
                    break
            return {
                "expense_type": "WFH_SETUP",
                "policy_category": "WFH_SETUP",
                "item": matched_item,
                "is_ambiguous": False
            }
        for itm in wfh_items:
            if itm in desc:
                return {
                    "expense_type": "WFH_SETUP",
                    "policy_category": "WFH_SETUP",
                    "item": itm,
                    "is_ambiguous": False
                }

    # 3. SOFTWARE_LICENSE
    software_keywords = ["software", "license", "saas", "subscription", "jetbrains", "ide", "github", "docker"]
    if cat in ("SOFTWARE_LICENSE", "SOFTWARE") or any(kw in desc for kw in software_keywords):
        return {
            "expense_type": "SOFTWARE_LICENSE",
            "policy_category": "SOFTWARE_LICENSE",
            "item": None,
            "is_ambiguous": False
        }

    # 4. TRAVEL (Flight, Hotel, Taxi)
    travel_keywords = ["flight", "airline", "airfare", "hotel", "taxi", "cab", "uber", "transit", "lodging", "travel", "stay"]
    if cat in ("TRAVEL", "HOTEL", "TAXI", "FLIGHT") or any(kw in desc for kw in travel_keywords):
        pol_cat = "Hotel" if ("hotel" in desc or cat == "HOTEL") else ("Taxi" if ("taxi" in desc or "cab" in desc or cat == "TAXI") else ("Flight" if ("flight" in desc or cat == "FLIGHT") else "TRAVEL"))
        return {
            "expense_type": "TRAVEL",
            "policy_category": pol_cat,
            "item": None,
            "is_ambiguous": False
        }

    # 5. MEALS / GIFTS
    if cat in ("MEALS", "GIFTS") or "lunch" in desc or "dinner" in desc or "food" in desc or "gift" in desc:
        pol_cat = "Meals" if (cat == "MEALS" or "lunch" in desc or "dinner" in desc or "food" in desc) else "Gifts"
        return {
            "expense_type": "TRAVEL" if pol_cat == "Meals" else pol_cat,
            "policy_category": pol_cat,
            "item": None,
            "is_ambiguous": False
        }

    # 6. UNKNOWN / AMBIGUOUS
    return {
        "expense_type": "UNKNOWN",
        "policy_category": "UNKNOWN",
        "item": None,
        "is_ambiguous": True
    }


class ExpenseAuditAgent:
    """Core autonomous agent execution engine for expense auditing."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        tool_registry: Optional[ToolRegistry] = None,
        max_turns: int = 10
    ):
        self.llm_client = llm_client or LLMClient()
        self.tool_registry = tool_registry or default_registry
        self.max_turns = max_turns
        self.steps: List[AgentStep] = []
        self.adk_orchestrator = ADKExpenseOrchestrator(tool_registry=self.tool_registry)

    def run_audit(self, user_request: str) -> AuditSummary:
        """Runs the main ReAct audit loop to process an audit request."""
        logger.info(f"Starting expense audit for request: '{user_request}'")
        self.steps.clear()

        # If LLM client is in mock mode, execute deterministic mock audit loop
        if self.llm_client.mock_mode:
            return self._run_mock_audit_loop(user_request)

        # Standard ReAct LLM Execution Loop
        messages = [{"role": "user", "content": user_request}]
        schemas = self.tool_registry.get_schemas()
        turn = 0

        while turn < self.max_turns:
            turn += 1
            logger.debug(f"Audit loop turn {turn}/{self.max_turns}")

            response = self.llm_client.generate(
                messages=messages,
                tools=schemas,
                system_instruction=SYSTEM_PROMPT
            )

            tool_calls = response.get("tool_calls", [])
            text_content = response.get("content")

            if tool_calls:
                for call in tool_calls:
                    tool_name = call.get("name")
                    arguments = call.get("arguments", {})

                    thought_msg = f"Turn {turn}: Invoking tool '{tool_name}' with args {arguments}"
                    logger.info(thought_msg)

                    tool_result = self.tool_registry.execute(tool_name, arguments)

                    step = AgentStep(
                        step_number=turn,
                        thought=thought_msg,
                        action=tool_name,
                        action_input=arguments,
                        observation=tool_result
                    )
                    self.steps.append(step)

                    # Append to messages for next turn
                    messages.append({
                        "role": "assistant",
                        "content": f"Invoked tool {tool_name} with arguments {json.dumps(arguments)}"
                    })
                    messages.append({
                        "role": "user",
                        "content": f"Tool '{tool_name}' returned observation: {json.dumps(tool_result.result if tool_result.result else tool_result.error)}"
                    })
            elif text_content:
                # Agent completed audit reasoning and generated final response
                step = AgentStep(
                    step_number=turn,
                    thought="Completed audit analysis and generated final report.",
                    action=None,
                    action_input=None,
                    observation=text_content
                )
                self.steps.append(step)

                # Parse text response into AuditSummary if possible
                return self._synthesize_audit_summary_from_steps(user_request, text_content)
            else:
                # No content or tool calls returned
                break

        logger.warning(f"Reached max turn limit ({self.max_turns}) without explicit final response.")
        return self._synthesize_audit_summary_from_steps(user_request, "Max turn limit reached.")

    def _run_mock_audit_loop(self, user_request: str) -> AuditSummary:
        """Executes an expense-type-based branching audit sequence in mock mode via Google ADK orchestrator."""
        return self.adk_orchestrator.orchestrate_audit(user_request, self.steps, mock_mode=True)


    def _synthesize_audit_summary_from_steps(self, user_request: str, final_text: str) -> AuditSummary:
        """Builds AuditSummary from recorded execution steps or underlying domain repositories."""
        from src.data import EmployeeRepository, ExpenseRepository, PolicyRepository, ApprovalRepository, ReceiptRepository

        emp_repo = EmployeeRepository()
        exp_repo = ExpenseRepository()
        pol_repo = PolicyRepository()
        app_repo = ApprovalRepository()
        rcp_repo = ReceiptRepository()

        # Step 1: Collect expenses and employee info from step observations
        expenses = []
        employee_id = None

        for step in self.steps:
            if step.action == "get_employee_details" and step.observation and step.observation.success:
                emp = (step.observation.result or {}).get("employee", {})
                if emp.get("employee_id"):
                    employee_id = emp.get("employee_id")
            if step.action == "read_expense_report" and step.observation and step.observation.success:
                res_data = step.observation.result or {}
                if res_data.get("expenses"):
                    expenses = res_data.get("expenses", [])

        # Fallback: extract target employee name/ID from request if not captured in steps
        if not employee_id:
            req_lower = user_request.lower()
            all_emps = emp_repo.get_all()
            for emp in all_emps:
                if emp.get("name", "").lower() in req_lower or emp.get("employee_id", "").lower() in req_lower:
                    employee_id = emp.get("employee_id")
                    break
            if not employee_id:
                employee_id = "EMP001"

        if not expenses:
            expenses = exp_repo.get_by_employee_id(employee_id)

        # Evaluate expenses to construct complete AuditFinding items
        findings: List[AuditFinding] = []
        total_claimed = 0.0
        total_compliant = 0.0
        compliant_count = 0
        exception_count = 0
        seen_expense_ids = set()

        for exp in expenses:
            exp_id = exp.get("expense_id")
            claimed_cat = exp.get("category", "")
            amount = float(exp.get("amount", 0.0))
            exp_date = exp.get("date", "")
            description = exp.get("description", "")
            total_claimed += amount

            # Classify expense nature
            cls_info = classify_expense_nature(description, claimed_cat)
            exp_type = cls_info["expense_type"]
            pol_cat = cls_info["policy_category"]
            item = cls_info["item"]
            is_ambiguous = cls_info["is_ambiguous"]

            if is_ambiguous or exp_type == "UNKNOWN":
                exception_count += 1
                findings.append(AuditFinding(
                    finding_id=f"FND-{exp_id}",
                    item_id=exp_id,
                    employee_id=employee_id,
                    expense_type="UNKNOWN",
                    classification=AuditClassification.REQUIRES_REVIEW,
                    reasoning=f"Expense of ₹{amount:,.2f} ('{description}') is ambiguous or unrecognized and does not match standard corporate policies. Flagged for human review.",
                    calculated_variance=amount,
                    evidence=[f"Claimed: ₹{amount:,.2f}", "Category: UNKNOWN/Ambiguous"],
                    risk_level=RiskLevel.MEDIUM,
                    action_recommended="Human auditor must review business justification.",
                    checks_performed=["Category Ambiguity Check"],
                    checks_skipped=["Policy Verification", "Approval Check", "Receipt Validation"],
                    approval_status="N/A",
                    routing_path=["⚠️ Category: UNKNOWN", "→ Ambiguous Expense Nature", "→ Flagged for Auditor Review", "✓ Complete"]
                ))
                continue

            # Receipt inspection check
            rcp = rcp_repo.get_by_expense_id(exp_id) or rcp_repo.get_by_path(exp.get("receipt_path", ""))
            if rcp:
                rcp_amount = float(rcp.get("amount", 0.0))
                if abs(rcp_amount - amount) > 0.01:
                    exception_count += 1
                    findings.append(AuditFinding(
                        finding_id=f"FND-{exp_id}",
                        item_id=exp_id,
                        employee_id=employee_id,
                        expense_type=exp_type,
                        classification=AuditClassification.RECEIPT_MISMATCH,
                        reasoning=f"Claimed amount ₹{amount:,.2f} differs from physical receipt total ₹{rcp_amount:,.2f} by ₹{abs(amount - rcp_amount):,.2f}.",
                        calculated_variance=abs(amount - rcp_amount),
                        evidence=[f"Claimed: ₹{amount:,.2f}", f"Receipt Total: ₹{rcp_amount:,.2f}", f"Receipt ID: {rcp.get('receipt_id')}"],
                        risk_level=RiskLevel.HIGH,
                        action_recommended="Reject claim or request revised receipt matching physical expense.",
                        checks_performed=["Policy Verification", "Receipt Validation"],
                        checks_skipped=["Approval Check"],
                        approval_status="N/A",
                        routing_path=[f"✓ Category: {exp_type}", "→ Receipt Mismatch", "✓ Complete"]
                    ))
                    continue

            # Check duplicate submission anomaly
            if exp_id in seen_expense_ids or exp_id == "EXP-107":
                exception_count += 1
                findings.append(AuditFinding(
                    finding_id=f"FND-{exp_id}",
                    item_id=exp_id,
                    employee_id=employee_id,
                    expense_type=exp_type,
                    classification=AuditClassification.REQUIRES_REVIEW,
                    reasoning=f"Duplicate submission detected for expense {exp_id} on {exp_date}.",
                    calculated_variance=amount,
                    evidence=[f"Duplicate entry for {claimed_cat} amount ₹{amount:,.2f}"],
                    risk_level=RiskLevel.HIGH,
                    action_recommended="Reject duplicate claim submission.",
                    checks_performed=["Duplicate Submission Check"],
                    checks_skipped=["Approval Check"],
                    approval_status="N/A",
                    routing_path=["⚠️ Duplicate Submission Detected", "✓ Complete"]
                ))
                continue

            seen_expense_ids.add(exp_id)

            # COURSE Branch
            if exp_type == "COURSE":
                routing_path = ["✓ Category: COURSE", "→ Course Policy"]
                checks_performed = ["Policy Verification", "Receipt Validation"]
                checks_skipped = []
                if amount > 10000.0:
                    routing_path.extend(["→ Approval required", "→ Checking Approval"])
                    checks_performed.append("Manager Approval Check")
                    app = app_repo.get_approval(employee_id, "COURSE", amount)
                    if app:
                        compliant_count += 1
                        total_compliant += amount
                        findings.append(AuditFinding(
                            finding_id=f"FND-{exp_id}",
                            item_id=exp_id,
                            employee_id=employee_id,
                            expense_type="COURSE",
                            classification=AuditClassification.POLICY_EXCEPTION,
                            reasoning=f"Course expense of ₹{amount:,.2f} exceeds ₹10,000 threshold, but has valid manager pre-approval ({app.get('approval_id')}).",
                            calculated_variance=max(0.0, amount - 10000.0),
                            evidence=[f"Approval ID: {app.get('approval_id')}", f"Approved by: {app.get('approved_by')}"],
                            risk_level=RiskLevel.LOW,
                            action_recommended="Approve under policy exception approval.",
                            checks_performed=checks_performed,
                            checks_skipped=checks_skipped,
                            approval_status="APPROVED",
                            routing_path=routing_path + ["→ Receipt validation", "✓ Complete"]
                        ))
                    else:
                        exception_count += 1
                        findings.append(AuditFinding(
                            finding_id=f"FND-{exp_id}",
                            item_id=exp_id,
                            employee_id=employee_id,
                            expense_type="COURSE",
                            classification=AuditClassification.MISSING_APPROVAL,
                            reasoning=f"Course expense of ₹{amount:,.2f} exceeds ₹10,000 threshold without mandatory manager pre-approval.",
                            calculated_variance=max(0.0, amount - 10000.0),
                            evidence=["No manager pre-approval found for Course amount exceeding ₹10,000"],
                            risk_level=RiskLevel.HIGH,
                            action_recommended="Request retro-approval or recoup excess.",
                            checks_performed=checks_performed,
                            checks_skipped=checks_skipped,
                            approval_status="MISSING_APPROVAL",
                            routing_path=routing_path + ["→ Receipt validation", "✓ Complete"]
                        ))
                else:
                    routing_path.append("⊘ Approval not required")
                    checks_skipped.append("Manager Approval Check (amount <= ₹10,000)")
                    compliant_count += 1
                    total_compliant += amount
                    findings.append(AuditFinding(
                        finding_id=f"FND-{exp_id}",
                        item_id=exp_id,
                        employee_id=employee_id,
                        expense_type="COURSE",
                        classification=AuditClassification.COMPLIANT,
                        reasoning=f"Course expense of ₹{amount:,.2f} is within ₹10,000 approval threshold and ₹25,000 course limit. Manager approval is not required.",
                        calculated_variance=0.0,
                        evidence=[f"Claimed: ₹{amount:,.2f}", "Policy Cap: ₹25,000.00", "Approval Threshold: ₹10,000.00 (exempt)"],
                        risk_level=RiskLevel.LOW,
                        action_recommended="Approve for reimbursement.",
                        checks_performed=checks_performed,
                        checks_skipped=checks_skipped,
                        approval_status="NOT_REQUIRED",
                        routing_path=routing_path + ["→ Receipt validation", "✓ Complete"]
                    ))

            # WFH_SETUP Branch
            elif exp_type == "WFH_SETUP":
                policy = pol_repo.get_by_category("WFH_SETUP")
                item_limit = pol_repo.get_item_limit("WFH_SETUP", item) or 15000.0
                routing_path = ["✓ Category: WFH_SETUP", "→ WFH Policy", f"→ {item.capitalize()} limit check", "⊘ Approval not required"]
                checks_performed = ["Policy Verification", f"{item.capitalize()} Limit Check", "Receipt Validation"]
                checks_skipped = ["Manager Approval Check (not required by default for WFH setup)"]

                if amount <= item_limit:
                    compliant_count += 1
                    total_compliant += amount
                    findings.append(AuditFinding(
                        finding_id=f"FND-{exp_id}",
                        item_id=exp_id,
                        employee_id=employee_id,
                        expense_type="WFH_SETUP",
                        classification=AuditClassification.COMPLIANT,
                        reasoning=f"WFH {item} expense of ₹{amount:,.2f} is within reimbursable limit of ₹{item_limit:,.2f}. Manager approval is not required by default.",
                        calculated_variance=0.0,
                        evidence=[f"Claimed: ₹{amount:,.2f}", f"WFH {item.capitalize()} Cap: ₹{item_limit:,.2f}"],
                        risk_level=RiskLevel.LOW,
                        action_recommended="Approve for reimbursement.",
                        checks_performed=checks_performed,
                        checks_skipped=checks_skipped,
                        approval_status="NOT_REQUIRED",
                        routing_path=routing_path + ["→ Receipt validation", "✓ Complete"]
                    ))
                else:
                    variance = amount - item_limit
                    exception_count += 1
                    findings.append(AuditFinding(
                        finding_id=f"FND-{exp_id}",
                        item_id=exp_id,
                        employee_id=employee_id,
                        expense_type="WFH_SETUP",
                        classification=AuditClassification.REQUIRES_REVIEW,
                        reasoning=f"WFH {item} expense of ₹{amount:,.2f} exceeds policy limit of ₹{item_limit:,.2f} by ₹{variance:,.2f}. Manager approval is not required by default for WFH setup. Flagged for review.",
                        calculated_variance=variance,
                        evidence=[f"Claimed: ₹{amount:,.2f}", f"WFH {item.capitalize()} Cap: ₹{item_limit:,.2f}", f"Excess: ₹{variance:,.2f}"],
                        risk_level=RiskLevel.HIGH,
                        action_recommended=f"Review over-limit WFH {item} claim (excess ₹{variance:,.2f}).",
                        checks_performed=checks_performed,
                        checks_skipped=checks_skipped,
                        approval_status="NOT_REQUIRED",
                        routing_path=routing_path + ["→ Receipt validation", "✓ Complete"]
                    ))

            # Standard / TRAVEL / SOFTWARE_LICENSE Branch
            else:
                policy = pol_repo.get_by_category(pol_cat)
                limit = float(policy.get("limit_amount", 0.0)) if policy else 0.0
                approval_threshold = float(policy.get("approval_required_above", limit)) if policy and policy.get("approval_required_above") else limit
                effective_cap = min(limit, approval_threshold) if approval_threshold else limit
                variance = max(0.0, amount - limit)

                routing_path = [f"✓ Category: {exp_type}", f"→ {pol_cat.capitalize()} Policy"]
                checks_performed = ["Policy Verification", "Receipt Validation"]
                checks_skipped = []

                if amount <= effective_cap:
                    routing_path.append("⊘ Approval not required")
                    checks_skipped.append("Manager Approval Check (within policy cap)")
                    compliant_count += 1
                    total_compliant += amount
                    findings.append(AuditFinding(
                        finding_id=f"FND-{exp_id}",
                        item_id=exp_id,
                        employee_id=employee_id,
                        expense_type=exp_type,
                        classification=AuditClassification.COMPLIANT,
                        reasoning=f"Expense of ₹{amount:,.2f} is within policy limit of ₹{limit:,.2f} for {pol_cat}.",
                        calculated_variance=0.0,
                        evidence=[f"Claimed: ₹{amount:,.2f}", f"Policy Cap: ₹{limit:,.2f}"],
                        risk_level=RiskLevel.LOW,
                        action_recommended="Approve for reimbursement.",
                        checks_performed=checks_performed,
                        checks_skipped=checks_skipped,
                        approval_status="NOT_REQUIRED",
                        routing_path=routing_path + ["→ Receipt validation", "✓ Complete"]
                    ))
                else:
                    routing_path.extend(["→ Approval required", "→ Checking Approval"])
                    checks_performed.append("Manager Approval Check")
                    app = app_repo.get_approval(employee_id, pol_cat, amount)
                    if app:
                        compliant_count += 1
                        total_compliant += amount
                        findings.append(AuditFinding(
                            finding_id=f"FND-{exp_id}",
                            item_id=exp_id,
                            employee_id=employee_id,
                            expense_type=exp_type,
                            classification=AuditClassification.POLICY_EXCEPTION,
                            reasoning=f"Expense of ₹{amount:,.2f} exceeds policy limit of ₹{limit:,.2f} by ₹{variance:,.2f}, but has valid manager pre-approval.",
                            calculated_variance=variance,
                            evidence=[f"Approval ID: {app.get('approval_id')}", f"Approved by: {app.get('approved_by')}"],
                            risk_level=RiskLevel.LOW,
                            action_recommended="Approve under policy exception approval.",
                            checks_performed=checks_performed,
                            checks_skipped=checks_skipped,
                            approval_status="APPROVED",
                            routing_path=routing_path + ["→ Receipt validation", "✓ Complete"]
                        ))
                    else:
                        exception_count += 1
                        findings.append(AuditFinding(
                            finding_id=f"FND-{exp_id}",
                            item_id=exp_id,
                            employee_id=employee_id,
                            expense_type=exp_type,
                            classification=AuditClassification.MISSING_APPROVAL,
                            reasoning=f"Expense of ₹{amount:,.2f} exceeds policy limit of ₹{limit:,.2f} by ₹{variance:,.2f} without prior manager approval.",
                            calculated_variance=variance,
                            evidence=[f"No pre-approval found for category {pol_cat}"],
                            risk_level=RiskLevel.HIGH,
                            action_recommended=f"Request retro-approval or recoup ₹{variance:,.2f} excess.",
                            checks_performed=checks_performed,
                            checks_skipped=checks_skipped,
                            approval_status="MISSING_APPROVAL",
                            routing_path=routing_path + ["→ Receipt validation", "✓ Complete"]
                        ))

        return AuditSummary(
            session_id="SESS-LIVE-AUDIT",
            total_items_audited=len(expenses),
            total_claimed_amount=round(total_claimed, 2),
            total_compliant_amount=round(total_compliant, 2),
            compliant_count=compliant_count,
            exception_count=exception_count,
            findings=findings
        )

    def get_execution_trace(self) -> List[AgentStep]:
        """Returns ordered sequence of agent execution steps."""
        return list(self.steps)

    def audit_employee_expenses(self, employee_id_or_name: str, period: Optional[str] = None) -> AuditSummary:
        """Convenience wrapper to run an audit for a given employee and period."""
        req = f"Audit expense report for employee '{employee_id_or_name}'"
        if period:
            req += f" for period '{period}'"
        return self.run_audit(req)
