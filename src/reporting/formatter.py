from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path
from src.models import AuditSummary, AuditFinding

class BaseReportGenerator(ABC):
    """Abstract Base Class for audit report generators."""

    @abstractmethod
    def generate(self, summary: AuditSummary) -> str:
        """Generates formatted report string from AuditSummary."""
        pass

    def export_to_file(self, summary: AuditSummary, output_path: Path) -> Path:
        """Exports generated report text to target file path."""
        content = self.generate(summary)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    @staticmethod
    def format_currency(amount: float, currency: str = "INR") -> str:
        """Formats float amount into currency string."""
        symbol = "₹" if currency == "INR" else "$"
        return f"{symbol}{amount:,.2f}"

    @staticmethod
    def calculate_total_variance(summary: AuditSummary) -> float:
        """Calculates total excess variance across all audit findings."""
        return sum(f.calculated_variance for f in summary.findings if f.calculated_variance > 0)
