class GenericException(Exception):
    pass


class ABIException(GenericException):
    """Exception for ABI data encoding errors"""

    pass


class EchidnaException(GenericException):
    """Exception for errros when interacting with Echidna"""

    pass


class CoverageException(GenericException):
    """Exception for errors during coverage generation"""
