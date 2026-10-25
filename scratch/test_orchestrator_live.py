import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.agent.adk_orchestrator import ADKExpenseOrchestrator
from src.models import AgentStep

orchestrator = ADKExpenseOrchestrator()
steps = []
print("Initializing ADK Orchestrator...")
print("Root agent model:", orchestrator.adk_root_agent.model)
print("Sub agents:", [sa.name for sa in orchestrator.adk_root_agent.sub_agents])
