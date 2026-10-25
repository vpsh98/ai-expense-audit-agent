import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from src.config import settings
from src.utils.logger import logger

class ApprovalRepository:
    """Repository for querying pre-approval records."""

    def __init__(self, data_path: Optional[Union[str, Path]] = None):
        self.data_path = Path(data_path) if data_path else settings.DATA_DIR / "approvals.json"
        self._approvals: List[Dict[str, Any]] = []
        self.load_data()

    def load_data(self) -> None:
        """Loads approval records from JSON file."""
        if not self.data_path.exists():
            logger.warning(f"Approval data file not found at {self.data_path}")
            self._approvals = []
            return
        
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                self._approvals = json.load(f)
            logger.info(f"Loaded {len(self._approvals)} approval records from {self.data_path}")
        except Exception as e:
            logger.error(f"Error loading approval data from {self.data_path}: {e}")
            self._approvals = []

    def get_all(self) -> List[Dict[str, Any]]:
        """Returns all approval records."""
        return list(self._approvals)

    def get_by_id(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Finds approval record by approval ID (case-insensitive)."""
        if not approval_id:
            return None
        target_id = approval_id.strip().upper()
        for app in self._approvals:
            if app.get("approval_id", "").strip().upper() == target_id:
                return app
        return None

    def get_by_employee_id(self, employee_id: str) -> List[Dict[str, Any]]:
        """Returns approvals for employee ID (case-insensitive)."""
        if not employee_id:
            return []
        target_id = employee_id.strip().upper()
        return [
            app for app in self._approvals
            if app.get("employee_id", "").strip().upper() == target_id
        ]

    def get_by_employee_and_category(self, employee_id: str, category: str) -> List[Dict[str, Any]]:
        """Returns approvals for employee ID and specific category (case-insensitive)."""
        if not employee_id or not category:
            return []
        target_id = employee_id.strip().upper()
        target_cat = category.strip().lower()
        return [
            app for app in self._approvals
            if app.get("employee_id", "").strip().upper() == target_id
            and app.get("category", "").strip().lower() == target_cat
        ]

    def get_approval_for_expense(
        self,
        employee_id: str,
        category: str,
        amount: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """Finds matching active approval for employee, category, and expense amount."""
        matching = self.get_by_employee_and_category(employee_id, category)
        for app in matching:
            if app.get("status", "").upper() == "APPROVED":
                max_amt = float(app.get("max_approved_amount", 0.0))
                if amount <= max_amt:
                    return app
        return None

    def get_approval(
        self,
        employee_id: str,
        category: str,
        amount: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """Alias for get_approval_for_expense."""
        return self.get_approval_for_expense(employee_id=employee_id, category=category, amount=amount)

