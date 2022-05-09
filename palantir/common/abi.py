from maat import Cst, Concat, Extract, Value
from .exceptions import ABIException
import sha3
from eth_abi.grammar import ABIType, BasicType, TupleType, parse, normalize
from eth_abi.exceptions import ABITypeError, ParseError
from typing import List, Union

# ====================================
# Methods that encode transaction data
# ====================================
def _check_int_bits(bits: int) -> None:
    """Raise an exception if bits is not in [0..256] or not
    a multiple of 8"""
    if bits % 8 != 0:
        raise ABIException("uint: bits must be multiple of 8")
    if bits <= 0:
        raise ABIException("uint: bits must be greater than zero")
    if bits > 256:
        raise ABIException("uint: bits can't exceed 256")


def uintM(bits: int, value: Union[int, Value]) -> Value:
    """Encode a uint<M>
    :param bits: number of bits <M>
    :param value: either a concrete value, the name of a symbolic variable, or a Value object
    """
    _check_int_bits(bits)

    if isinstance(value, int):
        return Cst(bits, value)
    elif isinstance(value, Value):
        if value.size == bits:
            return value
        # TODO(boyan): log warnings about type extension/truncation
        elif value.size < bits:
            return Extract(value, bits - 1, 0)
        else:
            return Concat(
                Cst(bits - value.size, 0), value
            )  # Zero extend because unsigned
    else:
        raise ABIException("'value' type must be int or str")


def selector(func_signature: str) -> bytes:
    """Return the first 4 bytes of the keccak256 hash of 'func_signature'"""
    k = sha3.keccak_256()
    k.update(func_signature.encode())
    return bytes(k.digest()[:4])


def call(func: str, args_spec: str, *args) -> List[Union[bytes, Value]]:
    """Encode a function call
    :param func: the name of the function to call
    :param args_spec: a string describing the type of arguments, e.g '(int256,bytes)' or 'uint'
    """
    # Parse function arguments
    try:
        args_spec = "".join(args_spec.split()) # strip all whitespaces
        args_spec = normalize(args_spec)
        args_types = parse(args_spec)
    except ParseError as e:
        raise ABIException(f"Error parsing args specification: {str(e)}")
    # Sanity check on supplied arguments
    try:
        args_types.validate()
    except ABITypeError as e:
        raise ABIException(f"Error in function args specification: {str(e)}")

    # Check number of arguments supplied
    if (
        isinstance(args_types, BasicType)
        and len(args) != 1
        or (
            isinstance(args_types, TupleType)
            and len(args) != len(args_types.components)
        )
    ):
        raise ABIException(
            "Number of supplied arguments don't match args specification"
        )

    # Compute function selector
    func_prototype = (
        f"{func}{args_spec}" if args_spec[0] == "(" else f"{func}({args_spec})"
    )
    res = [selector(func_prototype)]

    # Encode arguments
    for i, ty in enumerate(args_types.components):
        if ty.base == "uint":
            res.append(uintM(ty.sub, args[i]))
        else:
            raise ABIException(f"Unsupported type: {ty.base}")

    return res
