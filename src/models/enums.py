from enum import Enum

class AuditClassification(str, Enum):
    """Classification types for expense audit findings."""
    COMPLIANT = "COMPLIANT"
    POLICY_EXCEPTION = "POLICY_EXCEPTION"
    MISSING_APPROVAL = "MISSING_APPROVAL"
    RECEIPT_MISMATCH = "RECEIPT_MISMATCH"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class ExpenseCategory(str, Enum):
    """Standard corporate expense categories."""
    HOTEL = "Hotel"
    TAXI = "Taxi"
    MEALS = "Meals"
    GIFTS = "Gifts"
    FLIGHT = "Flight"
    COURSE = "COURSE"
    WFH_SETUP = "WFH_SETUP"
    TRAVEL = "TRAVEL"
    SOFTWARE_LICENSE = "SOFTWARE_LICENSE"
    OTHER = "Other"


class ExpenseType(str, Enum):
    """Canonical expense types for routing and branching."""
    COURSE = "COURSE"
    WFH_SETUP = "WFH_SETUP"
    TRAVEL = "TRAVEL"
    SOFTWARE_LICENSE = "SOFTWARE_LICENSE"
    UNKNOWN = "UNKNOWN"


class ApprovalStatus(str, Enum):
    """Pre-approval request statuses."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


class RiskLevel(str, Enum):
    """Audit finding severity/risk levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
