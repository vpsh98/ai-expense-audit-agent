import pytest
from src.tools import (
    GetEmployeeDetailsTool, get_employee_details,
    ReadExpenseReportTool, read_expense_report,
    SearchExpensePolicyTool, search_expense_policy,
    CheckApprovalTool, check_approval,
)

def test_get_employee_details_tool():
    # Lookup by ID
    res_id = get_employee_details(employee_id="EMP001")
    assert res_id.success is True
    assert res_id.result["found"] is True
    assert res_id.result["employee"]["name"] == "Rajesh Kumar"

    # Lookup by Name
    res_name = get_employee_details(employee_name="rajesh kumar")
    assert res_name.success is True
    assert res_name.result["found"] is True
    assert res_name.result["employee"]["employee_id"] == "EMP001"

    # Lookup nonexistent employee
    res_missing = get_employee_details(employee_id="EMP999")
    assert res_missing.success is True
    assert res_missing.result["found"] is False
    assert "not found" in res_missing.result["error"].lower()


def test_read_expense_report_tool():
    # Retrieve all expenses for EMP001
    res = read_expense_report(employee_id="EMP001")
    assert res.success is True
    assert res.result["count"] >= 3
    assert res.result["total_amount"] > 0

    # Retrieve expenses with period filter
    res_period = read_expense_report(employee_id="EMP001", period="2026-09")
    assert res_period.success is True
    assert res_period.result["count"] >= 3

    # Retrieve expenses with date range filter
    res_range = read_expense_report(
        employee_id="EMP001",
        start_date="2026-09-10",
        end_date="2026-09-10"
    )
    assert res_range.success is True
    assert res_range.result["count"] == 2  # EXP-101 and duplicate EXP-107


def test_search_expense_policy_tool_and_demo_validation():
    # Demo Validation: search_expense_policy(category="Hotel") returns max limit = 8000.0
    res_hotel = search_expense_policy(category="Hotel")
    assert res_hotel.success is True
    assert res_hotel.result["found"] is True
    assert res_hotel.result["limit_amount"] == 8000.0
    assert res_hotel.result["max_limit"] == 8000.0

    # Test Taxi policy
    res_taxi = search_expense_policy(category="Taxi")
    assert res_taxi.success is True
    assert res_taxi.result["limit_amount"] == 3000.0

    # Test missing policy category
    res_missing = search_expense_policy(category="NonExistentCategory")
    assert res_missing.success is True
    assert res_missing.result["found"] is False


def test_check_approval_tool():
    # Test valid pre-approval for Vikram Patel (Hotel ₹12,000 <= approved ₹15,000)
    res_app = check_approval(employee_id="EMP003", category="Hotel", amount=12000.0)
    assert res_app.success is True
    assert res_app.result["has_approval"] is True
    assert res_app.result["approval_id"] == "APP-2026-001"

    # Test no approval for Ananya Sharma (Taxi ₹4,500)
    res_no_app = check_approval(employee_id="EMP002", category="Taxi", amount=4500.0)
    assert res_no_app.success is True
    assert res_no_app.result["has_approval"] is False

    # Test amount exceeding pre-approved limit (₹20,000 > ₹15,000)
    res_exceed = check_approval(employee_id="EMP003", category="Hotel", amount=20000.0)
    assert res_exceed.success is True
    assert res_exceed.result["has_approval"] is False


def test_tool_json_schemas():
    tools = [
        GetEmployeeDetailsTool(),
        ReadExpenseReportTool(),
        SearchExpensePolicyTool(),
        CheckApprovalTool()
    ]
    for tool in tools:
        schema = tool.to_json_schema()
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
        assert schema["name"] == tool.name
