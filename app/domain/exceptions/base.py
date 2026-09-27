class DomainException(Exception):
    """Base class for all domain exceptions."""


class NotFoundError(DomainException):
    """Entity not found."""


class ValidationError(DomainException):
    """Input validation failed."""


class PermissionDeniedError(DomainException):
    """User has no permission for this action."""


class BusinessRuleViolation(DomainException):
    """Business rule was violated."""


class BudgetExceededError(BusinessRuleViolation):
    """Expense would exceed budget limit."""

    def __init__(self, category: str, used: str, limit: str) -> None:
        self.category = category
        self.used = used
        self.limit = limit
        super().__init__(f"Budget exceeded for '{category}': {used} / {limit}")


class InsufficientFundsError(BusinessRuleViolation):
    """Not enough balance for operation."""


class ExternalServiceError(DomainException):
    """An upstream service (e.g. the CBU rate API) is unavailable."""
