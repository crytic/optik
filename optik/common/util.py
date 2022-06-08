from maat import Value
from .exceptions import GenericException


def twos_complement_convert(arg: int, bits: int) -> int:
    """Takes an python integer and determines it's two's complement value
    in a given bit size

    :param arg: value to convert, interpreted as an unsigned value
    :param bits: bit length of 'arg'

    :return: two's complement integer of `arg` on `bits` length
    """
    if arg < 0:
        raise GenericException("Expected a positive value")
    elif arg >= (1 << bits):
        raise GenericException(f"Value {arg} too big to fit on {bits} bits")

    if arg & (1 << (bits - 1)) == 0:
        # Positive number
        return arg
    else:
        # Negative number
        return arg - (1 << bits)
