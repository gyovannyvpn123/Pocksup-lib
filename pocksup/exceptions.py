"""
Exceptions for the pocksup library.
"""

class PocksupException(Exception):
    """Base exception for all pocksup errors."""
    pass


class AuthenticationError(PocksupException):
    """Raised when there is an issue with authentication."""
    pass


class ConnectionError(PocksupException):
    """Raised when there is an issue with the connection to WhatsApp servers."""
    pass


class ProtocolError(PocksupException):
    """Raised when there is an error in the WhatsApp protocol implementation."""
    pass


class MediaError(PocksupException):
    """Raised when there is an error processing media."""
    pass


class BadParamError(PocksupException):
    """
    Raised when there is an issue with parameters.
    This is a specific improvement over yowsup's "bad_baram" error.
    """
    pass


class VersionError(PocksupException):
    """Raised when there is a version mismatch with the WhatsApp server."""
    pass


class RateLimitError(PocksupException):
    """Raised when rate limits are hit on WhatsApp servers."""
    pass


class ServerError(PocksupException):
    """Raised when the WhatsApp server returns an error."""
    pass
