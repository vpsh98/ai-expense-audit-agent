from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from src.tools.base import BaseTool
from src.data import EmployeeRepository

class GetEmployeeDetailsInput(BaseModel):
    """Input schema for get_employee_details tool."""
    employee_id: Optional[str] = Field(None, description="Employee ID (e.g. EMP001)")
    employee_name: Optional[str] = Field(None, description="Employee full name (e.g. Rajesh Kumar)")


class GetEmployeeDetailsTool(BaseTool):
    """Tool to retrieve employee profile and organization hierarchy details."""

    name: str = "get_employee_details"
    description: str = (
        "Get employee profile details including employee ID, full name, designation/grade, "
        "department, and manager name by employee ID or full name."
    )
    args_schema = GetEmployeeDetailsInput

    def __init__(self, employee_repo: Optional[EmployeeRepository] = None):
        super().__init__()
        self.employee_repo = employee_repo or EmployeeRepository()

    def _run(self, employee_id: Optional[str] = None, employee_name: Optional[str] = None) -> Any:
        if not employee_id and not employee_name:
            return {
                "found": False,
                "error": "Must provide either employee_id or employee_name.",
                "formatted_result": "Error: Must provide either employee_id or employee_name."
            }

        emp = None
        if employee_id:
            emp = self.employee_repo.get_by_id(employee_id)
        
        if not emp and employee_name:
            emp = self.employee_repo.get_by_name(employee_name)

        if not emp:
            query = employee_id or employee_name
            return {
                "found": False,
                "query": query,
                "error": f"Employee record not found for query '{query}'.",
                "formatted_result": f"Employee not found for '{query}'."
            }

        formatted = (
            f"Employee: {emp.get('name')} (ID: {emp.get('employee_id')})\n"
            f"Department: {emp.get('department')}\n"
            f"Designation: {emp.get('designation') or emp.get('grade')}\n"
            f"Manager: {emp.get('manager_name') or emp.get('manager')}"
        )

        return {
            "found": True,
            "employee": emp,
            "formatted_result": formatted
        }


# Global tool instance and function helper
get_employee_details_tool = GetEmployeeDetailsTool()

def get_employee_details(employee_id: Optional[str] = None, employee_name: Optional[str] = None):
    """Convenience function wrapper for get_employee_details tool."""
    return get_employee_details_tool.run(employee_id=employee_id, employee_name=employee_name)
