class BaseServiceException(Exception):
    """Base class for all business logic exceptions."""
    def __init__(self, message, code=None):
        self.message = message
        self.code = code or "service_error"
        super().__init__(self.message)

class ValidationError(BaseServiceException):
    """Raised when data fails business rule validation."""
    pass

class ResourceNotFoundError(BaseServiceException):
    """Raised when a required object (School, Class, etc.) is missing."""
    pass

class BusinessRuleViolation(BaseServiceException):
    """Raised when an action violates a specific school policy."""
    pass