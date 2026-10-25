import os
from typing import Any, Dict, List, Optional, Tuple
from google.adk import Agent
from src.config import settings
from src.tools import (
    search_expense_policy,
    check_approval,
    read_receipt,
    calculate,
)
from src.agent.tool_registry import ToolRegistry, default_registry
from src.models import (
    AuditClassification,
    AuditFinding,
    AgentStep,
    RiskLevel,
    ToolResult,
)
from src.utils.logger import logger

# Ensure Gemini API key is available in environment for Google ADK runners
if settings.GEMINI_API_KEY and not os.environ.get("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY


class BaseSpecialistAgent:
    """Base class for Google ADK specialist agents."""

    def __init__(
        self,
        name: str,
        description: str,
        instruction: str,
        tools: List[Any],
        model: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.name = name
        self.description = description
        self.instruction = instruction
        self.model = model or settings.LLM_MODEL
        self.tool_registry = tool_registry or default_registry

        # Instantiate Google ADK Agent backed by Gemini
        self.adk_agent = Agent(
            name=name,
            model=self.model,
            description=description,
            instruction=instruction,
            tools=tools,
        )

    def _record_tool_step(
        self,
        steps: List[AgentStep],
        turn_idx: int,
        thought: str,
        action: str,
        action_input: Dict[str, Any],
        observation: ToolResult,
    ) -> int:
        """Helper to append an AgentStep to the shared execution trace."""
        steps.append(
            AgentStep(
                step_number=turn_idx,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
            )
        )
        return turn_idx + 1


class CourseAgent(BaseSpecialistAgent):
    """Google ADK specialist agent for auditing COURSE / education expenses."""

    def __init__(self, model: Optional[str] = None, tool_registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="CourseAgent",
            model=model,
            description="Specialist agent that audits course, training, and certification expenses according to corporate education policy.",
            instruction=(
                "You are the Course Specialist Agent. Audit course, certification, and training expenses.\n"
                "1. Call search_expense_policy(category='COURSE') to get spending limits and approval criteria.\n"
                "2. Check if the claimed amount exceeds the ₹10,000 threshold:\n"
                "   - If amount > 10000: Manager approval is MANDATORY. You MUST call check_approval(employee_id=..., category='COURSE', amount=...).\n"
                "   - If amount <= 10000: Manager approval is NOT required. Do NOT call check_approval.\n"
                "3. Call read_receipt(expense_id=..., receipt_path=...) to validate receipt amount.\n"
                "4. Conclude with audit classification: COMPLIANT, POLICY_EXCEPTION, MISSING_APPROVAL, or RECEIPT_MISMATCH."
            ),
            tools=[search_expense_policy, check_approval, read_receipt],
            tool_registry=tool_registry,
        )

    def audit_expense(
        self,
        exp: Dict[str, Any],
        employee_id: str,
        steps: List[AgentStep],
        turn_idx: int,
    ) -> Tuple[AuditFinding, int]:
        exp_id = exp.get("expense_id") or exp.get("item_id")
        amount = float(exp.get("amount") or exp.get("claimed_amount", 0.0))
        receipt_path = exp.get("receipt_path")

        # 1. Retrieve Course Policy
        pol_res = self.tool_registry.execute("search_expense_policy", {"category": "COURSE"})
        turn_idx = self._record_tool_step(
            steps,
            turn_idx,
            thought="→ Course Policy: Query spending limits and approval criteria for COURSE",
            action="search_expense_policy",
            action_input={"category": "COURSE"},
            observation=pol_res,
        )

        routing_path = [
            "✓ Root Agent received request",
            "🔀 Routed to CourseAgent",
            "✓ Category: COURSE",
            "→ Course Policy",
        ]
        checks_performed = ["Policy Verification", "Receipt Validation"]
        checks_skipped = []
        variance = 0.0

        # 2. Check approval requirement threshold (₹10,000)
        if amount > 10000.0:
            routing_path.append("→ Approval required")
            routing_path.append("→ Checking Approval")
            app_res = self.tool_registry.execute(
                "check_approval",
                {"employee_id": employee_id, "category": "COURSE", "amount": amount},
            )
            turn_idx = self._record_tool_step(
                steps,
                turn_idx,
                thought=f"Course amount ₹{amount:,.2f} > ₹10,000 threshold: Manager approval required. Checking pre-approval.",
                action="check_approval",
                action_input={"employee_id": employee_id, "category": "COURSE", "amount": amount},
                observation=app_res,
            )
            checks_performed.append("Manager Approval Check")

            has_app = (
                app_res.result.get("has_approval", False)
                if app_res.success and app_res.result
                else False
            )
            if has_app:
                approval_status = "APPROVED"
                finding_classification = AuditClassification.POLICY_EXCEPTION
                variance = max(0.0, amount - 10000.0)
                evidence = [
                    f"Approval ID: {app_res.result.get('approval_id')}",
                    f"Approved by: {app_res.result.get('approved_by')}",
                ]
                reasoning = (
                    f"Course expense of ₹{amount:,.2f} exceeds ₹10,000 threshold, but has valid "
                    f"manager pre-approval ({app_res.result.get('approval_id')})."
                )
                action_rec = "Approve under course exception approval."
            else:
                approval_status = "MISSING_APPROVAL"
                finding_classification = AuditClassification.MISSING_APPROVAL
                variance = max(0.0, amount - 10000.0)
                evidence = ["No manager pre-approval found for Course amount exceeding ₹10,000"]
                reasoning = f"Course expense of ₹{amount:,.2f} exceeds ₹10,000 threshold without mandatory manager pre-approval."
                action_rec = "Request retro-approval or recoup excess."
        else:
            routing_path.append("⊘ Approval not required")
            checks_skipped.append("Manager Approval Check (amount <= ₹10,000)")
            approval_status = "NOT_REQUIRED"
            finding_classification = AuditClassification.COMPLIANT
            variance = 0.0
            evidence = [
                f"Claimed: ₹{amount:,.2f}",
                "Policy Cap: ₹25,000.00",
                "Approval Threshold: ₹10,000.00 (exempt)",
            ]
            reasoning = f"Course expense of ₹{amount:,.2f} is within ₹10,000 approval threshold and ₹25,000 course limit. Manager approval is not required."
            action_rec = "Approve for reimbursement."

        # 3. Receipt inspection check
        routing_path.append("→ Receipt validation")
        rcp_res = self.tool_registry.execute(
            "read_receipt", {"expense_id": exp_id, "receipt_path": receipt_path}
        )
        turn_idx = self._record_tool_step(
            steps,
            turn_idx,
            thought=f"Validate receipt documentation for course expense {exp_id}",
            action="read_receipt",
            action_input={"expense_id": exp_id, "receipt_path": receipt_path},
            observation=rcp_res,
        )

        if rcp_res.success and rcp_res.result and rcp_res.result.get("found"):
            rcp_amount = float(rcp_res.result.get("amount", 0.0))
            if abs(rcp_amount - amount) > 0.01:
                finding_classification = AuditClassification.RECEIPT_MISMATCH
                variance = abs(amount - rcp_amount)
                reasoning = f"Claimed amount ₹{amount:,.2f} differs from physical receipt total ₹{rcp_amount:,.2f}."
                evidence.append(f"Receipt Total: ₹{rcp_amount:,.2f}")

        routing_path.append("✓ Complete")

        finding = AuditFinding(
            finding_id=f"FND-{exp_id}",
            item_id=exp_id,
            employee_id=employee_id,
            expense_type="COURSE",
            classification=finding_classification,
            reasoning=reasoning,
            calculated_variance=variance,
            evidence=evidence,
            risk_level=RiskLevel.LOW
            if finding_classification in (AuditClassification.COMPLIANT, AuditClassification.POLICY_EXCEPTION)
            else RiskLevel.HIGH,
            action_recommended=action_rec,
            checks_performed=checks_performed,
            checks_skipped=checks_skipped,
            approval_status=approval_status,
            routing_path=routing_path,
        )
        return finding, turn_idx


class WfhSetupAgent(BaseSpecialistAgent):
    """Google ADK specialist agent for auditing WFH_SETUP equipment expenses."""

    def __init__(self, model: Optional[str] = None, tool_registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="WfhSetupAgent",
            model=model,
            description="Specialist agent that audits work-from-home (WFH) equipment expenses (monitor, keyboard, mouse, UPS, webcam, etc.).",
            instruction=(
                "You are the WFH Setup Specialist Agent. Audit work-from-home equipment claims (monitors, keyboards, mice, webcams, headphones, etc.).\n"
                "1. Call search_expense_policy(category='WFH_SETUP') to retrieve equipment reimbursement limits.\n"
                "2. IMPORTANT: Manager pre-approval is NOT required for standard WFH equipment. Skip manager approval. Do NOT call check_approval.\n"
                "3. Call read_receipt(expense_id=..., receipt_path=...) to validate receipt.\n"
                "4. If amount exceeds the policy limit for the specific item, call calculate to verify the excess variance.\n"
                "5. Conclude with final audit classification."
            ),
            tools=[search_expense_policy, calculate, read_receipt],
            tool_registry=tool_registry,
        )

    def audit_expense(
        self,
        exp: Dict[str, Any],
        employee_id: str,
        steps: List[AgentStep],
        turn_idx: int,
        item: Optional[str] = None,
    ) -> Tuple[AuditFinding, int]:
        exp_id = exp.get("expense_id") or exp.get("item_id")
        amount = float(exp.get("amount") or exp.get("claimed_amount", 0.0))
        description = exp.get("description", "")
        receipt_path = exp.get("receipt_path")

        # Determine item if not provided
        if not item:
            desc_lower = description.lower()
            wfh_items = ["monitor", "keyboard", "mouse", "ups", "earphones", "headphones", "webcam", "laptop stand", "docking station"]
            item = "monitor"
            for itm in wfh_items:
                if itm in desc_lower:
                    item = itm
                    break

        # 1. Retrieve WFH Policy for item
        pol_res = self.tool_registry.execute("search_expense_policy", {"category": "WFH_SETUP", "item": item})
        turn_idx = self._record_tool_step(
            steps,
            turn_idx,
            thought=f"→ WFH Policy: Query equipment policy for '{item}'",
            action="search_expense_policy",
            action_input={"category": "WFH_SETUP", "item": item},
            observation=pol_res,
        )

        item_limit = (
            float(pol_res.result.get("limit_amount", 15000.0))
            if pol_res.success and pol_res.result
            else 15000.0
        )
        routing_path = [
            "✓ Root Agent received request",
            "🔀 Routed to WfhSetupAgent",
            "✓ Category: WFH_SETUP",
            "→ WFH Policy",
            f"→ {item.capitalize()} limit check",
            "⊘ Approval not required",
        ]
        checks_performed = ["Policy Verification", f"{item.capitalize()} Limit Check", "Receipt Validation"]
        checks_skipped = ["Manager Approval Check (not required by default for WFH setup)"]
        approval_status = "NOT_REQUIRED"

        if amount <= item_limit:
            variance = 0.0
            finding_classification = AuditClassification.COMPLIANT
            evidence = [f"Claimed: ₹{amount:,.2f}", f"WFH {item.capitalize()} Cap: ₹{item_limit:,.2f}"]
            reasoning = (
                f"WFH {item} expense of ₹{amount:,.2f} is within reimbursable limit of "
                f"₹{item_limit:,.2f}. Manager approval is not required by default."
            )
            action_rec = "Approve for reimbursement."
        else:
            # Over item limit - compute exact variance via calculator tool
            calc_res = self.tool_registry.execute(
                "calculate", {"operation": "subtract", "a": amount, "b": item_limit}
            )
            turn_idx = self._record_tool_step(
                steps,
                turn_idx,
                thought=f"Calculate policy variance for WFH {item}",
                action="calculate",
                action_input={"operation": "subtract", "a": amount, "b": item_limit},
                observation=calc_res,
            )
            variance = (
                calc_res.result.get("value", amount - item_limit)
                if calc_res.success and calc_res.result
                else (amount - item_limit)
            )
            finding_classification = AuditClassification.REQUIRES_REVIEW
            evidence = [
                f"Claimed: ₹{amount:,.2f}",
                f"WFH {item.capitalize()} Cap: ₹{item_limit:,.2f}",
                f"Excess: ₹{variance:,.2f}",
            ]
            reasoning = (
                f"WFH {item} expense of ₹{amount:,.2f} exceeds reimbursable limit of "
                f"₹{item_limit:,.2f} by ₹{variance:,.2f}. Manager approval is not required "
                f"by default for WFH setup. Flagged for review."
            )
            action_rec = f"Review over-limit WFH {item} claim (excess ₹{variance:,.2f})."

        # 2. Receipt inspection check
        routing_path.append("→ Receipt validation")
        rcp_res = self.tool_registry.execute(
            "read_receipt", {"expense_id": exp_id, "receipt_path": receipt_path}
        )
        turn_idx = self._record_tool_step(
            steps,
            turn_idx,
            thought=f"Validate receipt documentation for WFH equipment {exp_id}",
            action="read_receipt",
            action_input={"expense_id": exp_id, "receipt_path": receipt_path},
            observation=rcp_res,
        )

        if rcp_res.success and rcp_res.result and rcp_res.result.get("found"):
            rcp_amount = float(rcp_res.result.get("amount", 0.0))
            if abs(rcp_amount - amount) > 0.01:
                finding_classification = AuditClassification.RECEIPT_MISMATCH
                variance = abs(amount - rcp_amount)
                reasoning = f"Claimed amount ₹{amount:,.2f} differs from physical receipt total ₹{rcp_amount:,.2f}."
                evidence.append(f"Receipt Total: ₹{rcp_amount:,.2f}")

        routing_path.append("✓ Complete")

        finding = AuditFinding(
            finding_id=f"FND-{exp_id}",
            item_id=exp_id,
            employee_id=employee_id,
            expense_type="WFH_SETUP",
            classification=finding_classification,
            reasoning=reasoning,
            calculated_variance=variance,
            evidence=evidence,
            risk_level=RiskLevel.LOW
            if finding_classification == AuditClassification.COMPLIANT
            else RiskLevel.HIGH,
            action_recommended=action_rec,
            checks_performed=checks_performed,
            checks_skipped=checks_skipped,
            approval_status=approval_status,
            routing_path=routing_path,
        )
        return finding, turn_idx


class TravelAgent(BaseSpecialistAgent):
    """Google ADK specialist agent for auditing corporate TRAVEL expenses (flight, hotel, taxi, meals)."""

    def __init__(self, model: Optional[str] = None, tool_registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="TravelAgent",
            model=model,
            description="Specialist agent that audits travel expenses (hotel, flight, taxi, meals) against standard corporate travel policies.",
            instruction=(
                "You are the Travel Specialist Agent. Audit travel expenses (hotel, flight, taxi, meals).\n"
                "1. Call search_expense_policy(category=...) to get limits.\n"
                "2. If amount exceeds limits, check manager approval using check_approval.\n"
                "3. Call read_receipt(expense_id=..., receipt_path=...) to validate receipt.\n"
                "4. If needed, call calculate to compute policy variance.\n"
                "5. Conclude with final audit classification."
            ),
            tools=[search_expense_policy, check_approval, read_receipt, calculate],
            tool_registry=tool_registry,
        )

    def audit_expense(
        self,
        exp: Dict[str, Any],
        employee_id: str,
        steps: List[AgentStep],
        turn_idx: int,
        pol_cat: str = "TRAVEL",
    ) -> Tuple[AuditFinding, int]:
        exp_id = exp.get("expense_id") or exp.get("item_id")
        amount = float(exp.get("amount") or exp.get("claimed_amount", 0.0))
        receipt_path = exp.get("receipt_path")

        # 1. Retrieve Policy
        pol_res = self.tool_registry.execute("search_expense_policy", {"category": pol_cat})
        turn_idx = self._record_tool_step(
            steps,
            turn_idx,
            thought=f"Lookup spending policy cap for category '{pol_cat}'",
            action="search_expense_policy",
            action_input={"category": pol_cat},
            observation=pol_res,
        )

        limit = float(pol_res.result.get("limit_amount", 0.0)) if pol_res.success and pol_res.result else 0.0
        approval_threshold = (
            float(pol_res.result.get("approval_required_above", limit))
            if pol_res.success and pol_res.result and pol_res.result.get("approval_required_above")
            else limit
        )
        effective_cap = min(limit, approval_threshold) if approval_threshold else limit

        routing_path = [
            "✓ Root Agent received request",
            "🔀 Routed to TravelAgent",
            "✓ Category: TRAVEL",
            f"→ {pol_cat.capitalize()} Policy",
        ]
        checks_performed = ["Policy Verification", "Receipt Validation"]
        checks_skipped = []

        # Calculate variance
        calc_res = self.tool_registry.execute(
            "calculate", {"operation": "subtract", "a": amount, "b": limit}
        )
        turn_idx = self._record_tool_step(
            steps,
            turn_idx,
            thought=f"Calculate policy variance for expense {exp_id}",
            action="calculate",
            action_input={"operation": "subtract", "a": amount, "b": limit},
            observation=calc_res,
        )
        variance = (
            calc_res.result.get("value", amount - limit)
            if calc_res.success and calc_res.result
            else (amount - limit)
        )

        # Receipt inspection check
        rcp_res = self.tool_registry.execute(
            "read_receipt", {"expense_id": exp_id, "receipt_path": receipt_path}
        )
        turn_idx = self._record_tool_step(
            steps,
            turn_idx,
            thought=f"Validate receipt documentation for expense {exp_id}",
            action="read_receipt",
            action_input={"expense_id": exp_id, "receipt_path": receipt_path},
            observation=rcp_res,
        )

        if rcp_res.success and rcp_res.result and rcp_res.result.get("found"):
            rcp_amount = float(rcp_res.result.get("amount", 0.0))
            if abs(rcp_amount - amount) > 0.01:
                finding = AuditFinding(
                    finding_id=f"FND-{exp_id}",
                    item_id=exp_id,
                    employee_id=employee_id,
                    expense_type="TRAVEL",
                    classification=AuditClassification.RECEIPT_MISMATCH,
                    reasoning=f"Claimed amount ₹{amount:,.2f} differs from physical receipt total ₹{rcp_amount:,.2f} by ₹{abs(amount - rcp_amount):,.2f}.",
                    calculated_variance=abs(amount - rcp_amount),
                    evidence=[
                        f"Claimed: ₹{amount:,.2f}",
                        f"Receipt Total: ₹{rcp_amount:,.2f}",
                        f"Receipt ID: {rcp_res.result.get('receipt_id')}",
                    ],
                    risk_level=RiskLevel.HIGH,
                    action_recommended="Reject claim or request revised receipt matching physical expense.",
                    checks_performed=checks_performed,
                    checks_skipped=checks_skipped,
                    approval_status="N/A",
                    routing_path=routing_path + ["→ Receipt Mismatch", "✓ Complete"],
                )
                return finding, turn_idx

        needs_approval = amount > effective_cap

        if not needs_approval:
            routing_path.append("⊘ Approval not required")
            checks_skipped.append("Manager Approval Check (within policy cap)")
            finding = AuditFinding(
                finding_id=f"FND-{exp_id}",
                item_id=exp_id,
                employee_id=employee_id,
                expense_type="TRAVEL",
                classification=AuditClassification.COMPLIANT,
                reasoning=f"Expense of ₹{amount:,.2f} is within policy limit of ₹{limit:,.2f} for {pol_cat}.",
                calculated_variance=0.0,
                evidence=[f"Claimed: ₹{amount:,.2f}", f"Policy Cap: ₹{limit:,.2f}"],
                risk_level=RiskLevel.LOW,
                action_recommended="Approve for reimbursement.",
                checks_performed=checks_performed,
                checks_skipped=checks_skipped,
                approval_status="NOT_REQUIRED",
                routing_path=routing_path + ["→ Receipt validation", "✓ Complete"],
            )
            return finding, turn_idx

        # Requires approval
        routing_path.append("→ Approval required")
        routing_path.append("→ Checking Approval")
        app_res = self.tool_registry.execute(
            "check_approval", {"employee_id": employee_id, "category": pol_cat, "amount": amount}
        )
        turn_idx = self._record_tool_step(
            steps,
            turn_idx,
            thought=f"Check pre-approval for expense {exp_id}",
            action="check_approval",
            action_input={"employee_id": employee_id, "category": pol_cat, "amount": amount},
            observation=app_res,
        )
        checks_performed.append("Manager Approval Check")

        has_app = (
            app_res.result.get("has_approval", False)
            if app_res.success and app_res.result
            else False
        )

        if has_app:
            finding = AuditFinding(
                finding_id=f"FND-{exp_id}",
                item_id=exp_id,
                employee_id=employee_id,
                expense_type="TRAVEL",
                classification=AuditClassification.POLICY_EXCEPTION,
                reasoning=f"Expense of ₹{amount:,.2f} exceeds policy limit of ₹{limit:,.2f} by ₹{variance:,.2f}, but has valid manager pre-approval.",
                calculated_variance=variance,
                evidence=[
                    f"Approval ID: {app_res.result.get('approval_id')}",
                    f"Approved by: {app_res.result.get('approved_by')}",
                ],
                risk_level=RiskLevel.LOW,
                action_recommended="Approve under policy exception approval.",
                checks_performed=checks_performed,
                checks_skipped=checks_skipped,
                approval_status="APPROVED",
                routing_path=routing_path + ["→ Receipt validation", "✓ Complete"],
            )
        else:
            finding = AuditFinding(
                finding_id=f"FND-{exp_id}",
                item_id=exp_id,
                employee_id=employee_id,
                expense_type="TRAVEL",
                classification=AuditClassification.MISSING_APPROVAL,
                reasoning=f"Expense of ₹{amount:,.2f} exceeds policy limit of ₹{limit:,.2f} by ₹{variance:,.2f} without prior manager approval.",
                calculated_variance=variance,
                evidence=[f"No pre-approval found for category {pol_cat}"],
                risk_level=RiskLevel.HIGH,
                action_recommended=f"Request retro-approval or recoup ₹{variance:,.2f} excess.",
                checks_performed=checks_performed,
                checks_skipped=checks_skipped,
                approval_status="MISSING_APPROVAL",
                routing_path=routing_path + ["→ Receipt validation", "✓ Complete"],
            )

        return finding, turn_idx


class SoftwareLicenseAgent(BaseSpecialistAgent):
    """Google ADK specialist agent for auditing SOFTWARE_LICENSE and developer tooling expenses."""

    def __init__(self, model: Optional[str] = None, tool_registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="SoftwareLicenseAgent",
            model=model,
            description="Specialist agent that audits software licenses, SaaS tools, and developer subscriptions.",
            instruction=(
                "You are the Software License Specialist Agent. Audit software licenses and SaaS tools.\n"
                "1. Call search_expense_policy(category='SOFTWARE_LICENSE') to get limits.\n"
                "2. If amount > 5000, call check_approval to verify manager pre-approval.\n"
                "3. Call read_receipt(expense_id=..., receipt_path=...) to validate receipt.\n"
                "4. Conclude with final audit classification."
            ),
            tools=[search_expense_policy, check_approval, read_receipt],
            tool_registry=tool_registry,
        )

    def audit_expense(
        self,
        exp: Dict[str, Any],
        employee_id: str,
        steps: List[AgentStep],
        turn_idx: int,
    ) -> Tuple[AuditFinding, int]:
        exp_id = exp.get("expense_id") or exp.get("item_id")
        amount = float(exp.get("amount") or exp.get("claimed_amount", 0.0))
        receipt_path = exp.get("receipt_path")

        # 1. Retrieve Policy
        pol_res = self.tool_registry.execute("search_expense_policy", {"category": "SOFTWARE_LICENSE"})
        turn_idx = self._record_tool_step(
            steps,
            turn_idx,
            thought="Lookup spending policy cap for category 'SOFTWARE_LICENSE'",
            action="search_expense_policy",
            action_input={"category": "SOFTWARE_LICENSE"},
            observation=pol_res,
        )

        limit = float(pol_res.result.get("limit_amount", 10000.0)) if pol_res.success and pol_res.result else 10000.0
        approval_threshold = (
            float(pol_res.result.get("approval_required_above", 5000.0))
            if pol_res.success and pol_res.result and pol_res.result.get("approval_required_above")
            else 5000.0
        )

        routing_path = [
            "✓ Root Agent received request",
            "🔀 Routed to SoftwareLicenseAgent",
            "✓ Category: SOFTWARE_LICENSE",
            "→ Software_license Policy",
        ]
        checks_performed = ["Policy Verification", "Receipt Validation"]
        checks_skipped = []
        variance = max(0.0, amount - limit)

        # Receipt inspection check
        rcp_res = self.tool_registry.execute(
            "read_receipt", {"expense_id": exp_id, "receipt_path": receipt_path}
        )
        turn_idx = self._record_tool_step(
            steps,
            turn_idx,
            thought=f"Validate receipt documentation for software license {exp_id}",
            action="read_receipt",
            action_input={"expense_id": exp_id, "receipt_path": receipt_path},
            observation=rcp_res,
        )

        if rcp_res.success and rcp_res.result and rcp_res.result.get("found"):
            rcp_amount = float(rcp_res.result.get("amount", 0.0))
            if abs(rcp_amount - amount) > 0.01:
                finding = AuditFinding(
                    finding_id=f"FND-{exp_id}",
                    item_id=exp_id,
                    employee_id=employee_id,
                    expense_type="SOFTWARE_LICENSE",
                    classification=AuditClassification.RECEIPT_MISMATCH,
                    reasoning=f"Claimed amount ₹{amount:,.2f} differs from physical receipt total ₹{rcp_amount:,.2f}.",
                    calculated_variance=abs(amount - rcp_amount),
                    evidence=[
                        f"Claimed: ₹{amount:,.2f}",
                        f"Receipt Total: ₹{rcp_amount:,.2f}",
                        f"Receipt ID: {rcp_res.result.get('receipt_id')}",
                    ],
                    risk_level=RiskLevel.HIGH,
                    action_recommended="Reject claim or request revised receipt matching physical expense.",
                    checks_performed=checks_performed,
                    checks_skipped=checks_skipped,
                    approval_status="N/A",
                    routing_path=routing_path + ["→ Receipt Mismatch", "✓ Complete"],
                )
                return finding, turn_idx

        # Approval check if amount > approval_threshold (₹5,000)
        if amount > approval_threshold:
            routing_path.append("→ Approval required")
            routing_path.append("→ Checking Approval")
            app_res = self.tool_registry.execute(
                "check_approval",
                {"employee_id": employee_id, "category": "SOFTWARE_LICENSE", "amount": amount},
            )
            turn_idx = self._record_tool_step(
                steps,
                turn_idx,
                thought=f"Software amount ₹{amount:,.2f} > ₹{approval_threshold:,.2f} threshold: Prior manager approval required.",
                action="check_approval",
                action_input={"employee_id": employee_id, "category": "SOFTWARE_LICENSE", "amount": amount},
                observation=app_res,
            )
            checks_performed.append("Manager Approval Check")

            has_app = (
                app_res.result.get("has_approval", False)
                if app_res.success and app_res.result
                else False
            )

            if has_app:
                approval_status = "APPROVED"
                finding = AuditFinding(
                    finding_id=f"FND-{exp_id}",
                    item_id=exp_id,
                    employee_id=employee_id,
                    expense_type="SOFTWARE_LICENSE",
                    classification=AuditClassification.POLICY_EXCEPTION,
                    reasoning=f"Software license expense of ₹{amount:,.2f} exceeds ₹{approval_threshold:,.2f} threshold, but has valid manager pre-approval.",
                    calculated_variance=variance,
                    evidence=[
                        f"Approval ID: {app_res.result.get('approval_id')}",
                        f"Approved by: {app_res.result.get('approved_by')}",
                    ],
                    risk_level=RiskLevel.LOW,
                    action_recommended="Approve under policy exception approval.",
                    checks_performed=checks_performed,
                    checks_skipped=checks_skipped,
                    approval_status=approval_status,
                    routing_path=routing_path + ["→ Receipt validation", "✓ Complete"],
                )
            else:
                approval_status = "MISSING_APPROVAL"
                finding = AuditFinding(
                    finding_id=f"FND-{exp_id}",
                    item_id=exp_id,
                    employee_id=employee_id,
                    expense_type="SOFTWARE_LICENSE",
                    classification=AuditClassification.MISSING_APPROVAL,
                    reasoning=f"Software license expense of ₹{amount:,.2f} exceeds ₹{approval_threshold:,.2f} threshold without prior manager approval.",
                    calculated_variance=variance,
                    evidence=["No manager pre-approval found for SOFTWARE_LICENSE exceeding ₹5,000 threshold"],
                    risk_level=RiskLevel.HIGH,
                    action_recommended="Request retro-approval or recoup excess.",
                    checks_performed=checks_performed,
                    checks_skipped=checks_skipped,
                    approval_status=approval_status,
                    routing_path=routing_path + ["→ Receipt validation", "✓ Complete"],
                )
        else:
            routing_path.append("⊘ Approval not required")
            checks_skipped.append("Manager Approval Check (within policy cap)")
            finding = AuditFinding(
                finding_id=f"FND-{exp_id}",
                item_id=exp_id,
                employee_id=employee_id,
                expense_type="SOFTWARE_LICENSE",
                classification=AuditClassification.COMPLIANT,
                reasoning=f"Software license expense of ₹{amount:,.2f} is within ₹{approval_threshold:,.2f} approval threshold.",
                calculated_variance=0.0,
                evidence=[f"Claimed: ₹{amount:,.2f}", f"Threshold: ₹{approval_threshold:,.2f}"],
                risk_level=RiskLevel.LOW,
                action_recommended="Approve for reimbursement.",
                checks_performed=checks_performed,
                checks_skipped=checks_skipped,
                approval_status="NOT_REQUIRED",
                routing_path=routing_path + ["→ Receipt validation", "✓ Complete"],
            )

        return finding, turn_idx
