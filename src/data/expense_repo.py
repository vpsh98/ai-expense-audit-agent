import csv
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from src.config import settings
from src.utils.logger import logger

class ExpenseRepository:
    """Repository for querying expense records from CSV."""

    def __init__(self, data_path: Optional[Union[str, Path]] = None):
        self.data_path = Path(data_path) if data_path else settings.DATA_DIR / "expenses.csv"
        self._expenses: List[Dict[str, Any]] = []
        self.load_data()

    def load_data(self) -> None:
        """Loads expense records from CSV file."""
        if not self.data_path.exists():
            logger.warning(f"Expense data file not found at {self.data_path}")
            self._expenses = []
            return
        
        try:
            expenses = []
            with open(self.data_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert numeric fields
                    try:
                        row["amount"] = float(row["amount"])
                    except (ValueError, KeyError, TypeError):
                        row["amount"] = 0.0

                    # Normalize date format to YYYY-MM-DD (e.g. 10-09-2026 -> 2026-09-10)
                    exp_date = str(row.get("date", "")).strip()
                    if len(exp_date) == 10 and exp_date[2] == '-' and exp_date[5] == '-':
                        parts = exp_date.split("-")
                        if len(parts[2]) == 4:
                            row["date"] = f"{parts[2]}-{parts[1]}-{parts[0]}"

                    expenses.append(row)
            self._expenses = expenses
            logger.info(f"Loaded {len(self._expenses)} expenses from {self.data_path}")
        except Exception as e:
            logger.error(f"Error loading expense data from {self.data_path}: {e}")
            self._expenses = []

    def get_all(self) -> List[Dict[str, Any]]:
        """Returns all expense records."""
        self.load_data()
        return list(self._expenses)

    def get_by_id(self, expense_id: str) -> Optional[Dict[str, Any]]:
        """Finds expense by ID (case-insensitive)."""
        self.load_data()
        if not expense_id:
            return None
        target_id = expense_id.strip().upper()
        for exp in self._expenses:
            if exp.get("expense_id", "").strip().upper() == target_id:
                return exp
        return None

    def get_by_employee_id(self, employee_id: str) -> List[Dict[str, Any]]:
        """Returns all expenses submitted by employee ID (case-insensitive)."""
        self.load_data()
        if not employee_id:
            return []
        target_id = employee_id.strip().upper()
        return [
            exp for exp in self._expenses
            if exp.get("employee_id", "").strip().upper() == target_id
        ]

    def get_by_employee_name(self, name: str) -> List[Dict[str, Any]]:
        """Returns all expenses submitted by employee name (case-insensitive)."""
        if not name:
            return []
        target_name = name.strip().lower()
        return [
            exp for exp in self._expenses
            if exp.get("employee_name", "").strip().lower() == target_name
        ]

    def get_expenses_by_date_range(
        self,
        start_date: str,
        end_date: str,
        employee_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filters expenses within date range [start_date, end_date] (YYYY-MM-DD)."""
        filtered = self._expenses
        if employee_id:
            target_id = employee_id.strip().upper()
            filtered = [
                exp for exp in filtered
                if exp.get("employee_id", "").strip().upper() == target_id
            ]

        results = []
        for exp in filtered:
            exp_date = exp.get("date", "")
            if start_date <= exp_date <= end_date:
                results.append(exp)
        return results

    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Returns all expenses matching category (case-insensitive)."""
        if not category:
            return []
        target_cat = category.strip().lower()
        return [
            exp for exp in self._expenses
            if exp.get("category", "").strip().lower() == target_cat
        ]
