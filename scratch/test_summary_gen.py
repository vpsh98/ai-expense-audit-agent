import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.config import settings
os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY

from src.agent.specialists import CourseAgent, WfhSetupAgent, TravelAgent, SoftwareLicenseAgent
from src.agent.adk_orchestrator import ADKExpenseOrchestrator
from src.models import AgentStep, AuditClassification

orchestrator = ADKExpenseOrchestrator()

# Test 1: Course Claim
steps_course = []
print("Testing Course Claim Audit...")
summary_course = orchestrator.orchestrate_audit("Audit my ₹18,000 AWS certification course", steps_course, mock_mode=False)
print("Course Items:", summary_course.total_items_audited)
print("Course Findings:", len(summary_course.findings))
if summary_course.findings:
    f = summary_course.findings[0]
    print(f"Course Finding: ID={f.item_id}, Class={f.classification}, Approval={f.approval_status}")
    print(f"Routing path: {f.routing_path}")
print(f"Steps count: {len(steps_course)}")
for s in steps_course:
    print(f"  Step {s.step_number}: action={s.action} thought={s.thought}")

# Test 2: WFH Claim
steps_wfh = []
print("\nTesting WFH Claim Audit...")
summary_wfh = orchestrator.orchestrate_audit("Audit my ₹12,000 monitor purchase for home office", steps_wfh, mock_mode=False)
print("WFH Items:", summary_wfh.total_items_audited)
print("WFH Findings:", len(summary_wfh.findings))
if summary_wfh.findings:
    f = summary_wfh.findings[0]
    print(f"WFH Finding: ID={f.item_id}, Class={f.classification}, Approval={f.approval_status}")
    print(f"Routing path: {f.routing_path}")
print(f"Steps count: {len(steps_wfh)}")
for s in steps_wfh:
    print(f"  Step {s.step_number}: action={s.action} thought={s.thought}")
