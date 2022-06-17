from maat import Value
from .exceptions import GenericException
from .logger import logger

import re


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

# textual unicode symbols not handled by python's unicode decode
UNICODE_SYMBOLS = [
    "NUL", "SOH", "STX", "ETX", "EOT", "ENQ", "ACK", "BEL", "BS", "HT", "LF", "VT", "FF", "CR", "SO", "SI", "dle", "DC1", "DC2", "DC3", "DC4", "NAK", "SYN", "ETB", "CAN", "EM", "SUB", "ESC", "FS", "GS", "RS", "US"
]

def parse_bytes(unicode_str: str) -> list[int]:
    """Takes a json + unicode encoded string and converts it
    to a list of bytes

    :param unicode_str: the json, unciode encoded string

    :return list of bytes (big byte order) of the original bytes
    """

    # convert values to bytes for parsing
    unicode_str = unicode_str.encode('utf-8') 
    
    """
    The bytes strings we receive are unicode encoded, but characters are escaped with decimal values,
    and with textual representatives of unicode characters (such as `STX`). Neither of these
    are supported by Python decoding or any libraries, so we convert them to a form which
    is supported, and then proceed with decoding.
    """
    # https://stackoverflow.com/questions/21300996/process-decimal-escape-in-string
    def replaceDecimals(match):
        """Converts escaped decimal characters to hexadecimal
        """
        return int(match.group(1)).to_bytes(1, byteorder='big')

    def replaceTextual(match):
        """Converts text-based unicode escaped characters into their 
        decimal representation, i.e. `\STX` -> `\u0003`
        """
        sym = match.group(1).decode()
        if sym not in UNICODE_SYMBOLS:
            raise GenericException(f"Unknown unicode escape sequence {sym}")

        return bytes("\\u" + str(UNICODE_SYMBOLS.index(sym)).zfill(4), 'utf-8')

    # convert instances of escaped decimal values to escaped hexadecimal
    # regex: match `\XXX` where `X` is a decimal digit
    regex = re.compile(rb"\\(\d{1,3})")
    unicode_str = regex.sub(replaceDecimals, unicode_str)

    # convert escaped text unicode characters to their `\uXXXX` equivalent
    # regex: unicode texts are either 2 or 3 characters long, comprised 
    #   of letters, or numbers from 1-4
    regex = re.compile(rb"\\([A-Z1-4]{2,3})")
    logger.debug(f"Type now: {type(unicode_str)} with val: {unicode_str}")
    unicode_str = regex.sub(replaceTextual, unicode_str)

    # all escape characters should be python-decodeable now
    unicode_str = unicode_str.decode('unicode_escape')
    unicode_str = unicode_str.encode('utf-8') # convert back to bytes

    return [byte for byte in unicode_str]

def echidna_byte_converter(byte_vals: list[int]) -> str:
    """Inverse function to `parse_bytes`, it converts a list of bytes into
    the cursed unicode format that `echidna` requires, with decimal encoded codes
    and textual escape sequences
    """
    raise NotImplementedError





