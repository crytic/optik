from maat import Value
from .exceptions import GenericException
from .logger import logger
import re
from typing import Union, List, Tuple, Dict
import rlp
import sha3


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
_UNICODE_SYMBOLS = [
    "NUL",
    "SOH",
    "STX",
    "ETX",
    "EOT",
    "ENQ",
    "ACK",
    "BEL",
    "BS",
    "HT",
    "LF",
    "VT",
    "FF",
    "CR",
    "SO",
    "SI",
    "DLE",
    "DC1",
    "DC2",
    "DC3",
    "DC4",
    "NAK",
    "SYN",
    "ETB",
    "CAN",
    "EM",
    "SUB",
    "ESC",
    "FS",
    "GS",
    "RS",
    "US",
]
UNICODE_SYMBOLS = dict()
for i, s in enumerate(_UNICODE_SYMBOLS):
    UNICODE_SYMBOLS[i] = s
    UNICODE_SYMBOLS[s] = i
UNICODE_SYMBOLS.update({"DEL": 0x7F, 0x7F: "DEL"})


def echidna_parse_bytes(unicode_str: str) -> List[int]:
    """Takes a json + unicode encoded string and converts it
    to a list of bytes

    :param unicode_str: the json, unicode encoded string

    :return list of bytes (big byte order) of the original bytes
    """

    # convert values to bytes for parsing
    unicode_str = unicode_str.encode("utf-8")

    """
    The bytes strings we receive are unicode encoded, but characters are escaped with decimal values,
    and with textual representatives of unicode characters (such as `STX`). Neither of these
    are supported by Python decoding or any libraries, so we convert them to a form which
    is supported, and then proceed with decoding.
    """
    # https://stackoverflow.com/questions/21300996/process-decimal-escape-in-string
    def replaceDecimals(match) -> bytes:
        """Converts escaped decimal characters to hexadecimal"""
        return int(match.group(1)).to_bytes(1, byteorder="big")

    def replaceTextual(match) -> bytes:
        """Converts text-based unicode escaped characters into their
        decimal representation, i.e. `\STX` -> `\u0003`
        """
        sym = match.group(1).decode()
        if sym not in UNICODE_SYMBOLS:
            raise GenericException(f"Unknown unicode escape sequence {sym}")

        return UNICODE_SYMBOLS[sym].to_bytes(1, byteorder="big")

    unicode_str = unicode_str[1:-1]  # remove double quoted string

    # convert instances of escaped decimal values to escaped hexadecimal
    # regex: match `\XXX` where `X` is a decimal digit
    regex = re.compile(rb"\\(\d{1,3})")
    unicode_str = regex.sub(replaceDecimals, unicode_str)

    # convert escaped text unicode characters to their `\uXXXX` equivalent
    # regex: unicode texts are either 2 or 3 characters long, comprised
    #   of letters, or numbers from 1-4
    regex = re.compile(rb"\\([A-Z1-4]{2,3})")
    unicode_str = regex.sub(replaceTextual, unicode_str)

    return list(unicode_str)


def echidna_encode_bytes(string: bytes) -> str:
    """Inverse function to `parse_bytes`, it converts a python string into
    the unicode format that `echidna` requires, with decimal encoded codes
    and textual escape sequences
    """
    res = ""
    for b in string:
        if b in UNICODE_SYMBOLS:
            res += f"\\{UNICODE_SYMBOLS[b]}"
        else:
            if b <= 0x7E:  # '~' is biggest printable char
                res += chr(b)
            else:
                res += f"\\{b}"
    res = f'"{res}"'
    return res


def list_has_types(
    val: Union[List[type], Tuple[type]], wanted_type: type
) -> bool:
    """Validates that all elements of a given list are of type `wanted_type`

    :param val: the list to inspect types for
    :param wanted_type: the type that all values of `val` should be

    :return: True if all elements of `val` are of type `wanted_type`, otherwise False
    """

    # `val` should be a list
    if not isinstance(val, list) and not isinstance(val, tuple):
        return False

    # If any single value is not of type `wanted_type`, then False
    if any([v for v in val if not isinstance(v, wanted_type)]):
        return False

    return True


def int_to_bool(arg: int) -> bool:
    """Takes a python integer and converts it to a boolean value.

    :param arg: value to convert, integer representing a bool

    :return False if arg is 0, True otherwise"""

    if arg < 0:
        raise GenericException("Expected a positive value")

    return arg != 0


def compute_new_contract_addr(sender: int, nonce: int) -> int:
    """Compute a new contract address as generated by the CREATE instruction
    originating from 'sender' with nonce 'nonce'"""

    k = sha3.keccak_256()
    k.update(rlp.encode([sender.to_bytes(20, "big"), nonce]))
    digest = k.digest()[12:]
    return int.from_bytes(digest, "big")
