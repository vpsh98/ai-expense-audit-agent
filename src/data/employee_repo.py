import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from src.config import settings
from src.utils.logger import logger

class EmployeeRepository:
    """Repository for querying employee records."""

    def __init__(self, data_path: Optional[Union[str, Path]] = None):
        self.data_path = Path(data_path) if data_path else settings.DATA_DIR / "employees.json"
        self._employees: List[Dict[str, Any]] = []
        self.load_data()

    def load_data(self) -> None:
        """Loads employee records from JSON file."""
        if not self.data_path.exists():
            logger.warning(f"Employee data file not found at {self.data_path}")
            self._employees = []
            return
        
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                self._employees = json.load(f)
            logger.info(f"Loaded {len(self._employees)} employees from {self.data_path}")
        except Exception as e:
            logger.error(f"Error loading employee data from {self.data_path}: {e}")
            self._employees = []

    def get_all(self) -> List[Dict[str, Any]]:
        """Returns all employee records."""
        return list(self._employees)

    def get_by_id(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Finds employee by ID (case-insensitive)."""
        if not employee_id:
            return None
        target_id = employee_id.strip().upper()
        for emp in self._employees:
            if emp.get("employee_id", "").strip().upper() == target_id:
                return emp
        return None

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Finds employee by name (case-insensitive)."""
        if not name:
            return None
        target_name = name.strip().lower()
        for emp in self._employees:
            if emp.get("name", "").strip().lower() == target_name:
                return emp
        return None

    def get_by_department(self, department: str) -> List[Dict[str, Any]]:
        """Returns all employees in a specific department (case-insensitive)."""
        if not department:
            return []
        target_dept = department.strip().lower()
        return [
            emp for emp in self._employees
            if emp.get("department", "").strip().lower() == target_dept
        ]
