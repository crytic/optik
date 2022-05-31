class GenericException(Exception):
    """Generic exception class for Palantir, from which all custom
    exceptions derive"""

    pass


class ABIException(GenericException):
    """Exception for ABI data encoding errors"""

    pass


class EchidnaException(GenericException):
    """Exception for errros when interacting with Echidna"""

    pass


class CoverageException(GenericException):
    """Exception for errors during coverage generation"""

    pass


class WorldException(GenericException):
    """Exception for errors in execution wrappers for the contracts
    deployed on the blockchain"""

    pass
