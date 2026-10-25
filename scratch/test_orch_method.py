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
from src.models import AgentStep

orchestrator = ADKExpenseOrchestrator()
steps = []
print("Testing live orchestrate_audit on Course claim...")
summary = orchestrator.orchestrate_audit("Audit my ₹18,000 AWS certification course", steps, mock_mode=False)
print("Summary session:", summary.session_id)
print("Total items audited:", summary.total_items_audited)
print("Findings count:", len(summary.findings))
if summary.findings:
    f = summary.findings[0]
    print("Finding classification:", f.classification)
    print("Routing path:", f.routing_path)
print("Recorded steps count:", len(steps))
for s in steps:
    print(f" - Step {s.step_number}: action={s.action} thought={s.thought[:60]}...")
