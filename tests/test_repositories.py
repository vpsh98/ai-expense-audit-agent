import pytest
from pathlib import Path
from src.data import (
    EmployeeRepository,
    ExpenseRepository,
    ApprovalRepository,
    PolicyRepository,
)

def test_employee_repository():
    repo = EmployeeRepository()
    employees = repo.get_all()
    assert len(employees) > 0

    # Test case-insensitive ID lookup
    emp_upper = repo.get_by_id("EMP001")
    emp_lower = repo.get_by_id("emp001")
    assert emp_upper is not None
    assert emp_lower is not None
    assert emp_upper["name"] == "Rajesh Kumar"
    assert emp_lower["name"] == "Rajesh Kumar"

    # Test case-insensitive Name lookup
    emp_by_name = repo.get_by_name("rajesh kumar")
    assert emp_by_name is not None
    assert emp_by_name["employee_id"] == "EMP001"

    # Test department query
    sales_emps = repo.get_by_department("Sales")
    assert any(e["employee_id"] == "EMP001" for e in sales_emps)

    # Test invalid lookup
    assert repo.get_by_id("INVALID_ID") is None
    assert repo.get_by_name("Nonexistent Person") is None


def test_expense_repository_and_rajesh_september_demo():
    repo = ExpenseRepository()
    expenses = repo.get_all()
    assert len(expenses) > 0

    # Demo validation check: Resolve Rajesh Kumar's September expense records
    rajesh_sept = repo.get_expenses_by_date_range(
        start_date="2026-09-01",
        end_date="2026-09-30",
        employee_id="EMP001"
    )
    assert len(rajesh_sept) >= 3
    for exp in rajesh_sept:
        assert exp["employee_id"] == "EMP001"
        assert exp["date"].startswith("2026-09")
        assert isinstance(exp["amount"], float)

    # Test lookup by ID
    exp_101 = repo.get_by_id("EXP-101")
    assert exp_101 is not None
    assert exp_101["merchant"] == "Bistro Central"

    # Test lookup by employee name
    exp_by_name = repo.get_by_employee_name("rajesh kumar")
    assert len(exp_by_name) >= 3

    # Test category filtering
    hotel_expenses = repo.get_by_category("Hotel")
    assert len(hotel_expenses) >= 2


def test_approval_repository():
    repo = ApprovalRepository()
    approvals = repo.get_all()
    assert len(approvals) > 0

    # Test lookup by ID
    app = repo.get_by_id("APP-2026-001")
    assert app is not None
    assert app["employee_id"] == "EMP003"
    assert app["category"] == "Hotel"
    assert app["max_approved_amount"] == 15000.0

    # Test lookup by employee and category
    emp3_hotel_apps = repo.get_by_employee_and_category("EMP003", "hotel")
    assert len(emp3_hotel_apps) == 1

    # Test matching approval for expense amount
    valid_app = repo.get_approval_for_expense("EMP003", "Hotel", 12000.0)
    assert valid_app is not None
    assert valid_app["approval_id"] == "APP-2026-001"

    # Exceeding pre-approved limit should return None
    invalid_app = repo.get_approval_for_expense("EMP003", "Hotel", 20000.0)
    assert invalid_app is None


def test_policy_repository():
    repo = PolicyRepository()
    policies = repo.get_all()
    assert len(policies) >= 5

    # Check limits for standard categories
    assert repo.get_limit_for_category("Hotel") == 8000.0
    assert repo.get_limit_for_category("taxi") == 3000.0
    assert repo.get_limit_for_category("MEALS") == 1500.0
    assert repo.get_limit_for_category("Gifts") == 5000.0
    assert repo.get_limit_for_category("Flight") == 25000.0

    # Check non-existent category
    assert repo.get_by_category("Rocket") is None
    assert repo.get_limit_for_category("Rocket") is None


def test_custom_data_path(tmp_path: Path):
    # Test custom path fallback when file does not exist
    custom_emp = tmp_path / "custom_employees.json"
    repo = EmployeeRepository(data_path=custom_emp)
    assert repo.get_all() == []

    # Write custom data and verify reloading
    custom_emp.write_text('[{"employee_id": "TEST01", "name": "Test User"}]', encoding="utf-8")
    repo.load_data()
    assert len(repo.get_all()) == 1
    assert repo.get_by_id("TEST01")["name"] == "Test User"
