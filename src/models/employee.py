from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class Employee(BaseModel):
    """Employee entity model."""
    model_config = ConfigDict(populate_by_name=True)

    employee_id: str = Field(..., description="Unique employee identifier (e.g., EMP001)")
    name: str = Field(..., description="Full name of the employee")
    email: Optional[str] = Field(None, description="Employee email address")
    department: Optional[str] = Field(None, description="Department name (e.g. Sales, Engineering)")
    grade: Optional[str] = Field(None, description="Employee grade/level")
    designation: Optional[str] = Field(None, description="Job title / designation")
    manager: Optional[str] = Field(None, description="Manager name or ID")
    manager_id: Optional[str] = Field(None, description="Manager employee ID")
    manager_name: Optional[str] = Field(None, description="Manager full name")
