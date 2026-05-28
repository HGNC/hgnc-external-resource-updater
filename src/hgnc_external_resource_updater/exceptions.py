"""Domain-specific exception hierarchy for the HGNC external resource updater."""


class ServiceError(Exception):
    """Base exception for all domain errors."""


class ConfigError(ServiceError):
    """Raised when configuration is invalid or missing."""


class RepositoryError(ServiceError):
    """Raised when a database or data access operation fails."""


class FetchError(ServiceError):
    """Raised when fetching data from an external source fails."""


class ParseError(ServiceError):
    """Raised when parsing external feed data fails."""


class ValidationError(ServiceError):
    """Raised when domain validation of a record fails."""


class PersistenceError(ServiceError):
    """Raised when a database write or update operation fails."""
