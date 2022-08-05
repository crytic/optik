# pylint: disable=unnecessary-pass
class GenericException(Exception):
    """Generic exception class for Optik, from which all custom
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


class CorpusException(GenericException):
    """Exception for errors during corpus generation"""

    pass


class DataflowException(GenericException):
    """Exception for errors during dataflow analysis"""

    pass


class InitializationError(Exception):
    """Error in while optik initializes"""

    pass


class ArgumentParsingError(GenericException):
    """Error parsing command line arguments with argparse"""

    def __init__(self, msg, help_str) -> None:
        self.msg = msg
        self.help_str = help_str
