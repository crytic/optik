from maat import Cst, Concat, Extract, Value
from .exceptions import ABIException
import sha3
from eth_abi.grammar import ABIType, BasicType, TupleType, parse, normalize
from eth_abi.exceptions import ABITypeError, ParseError
from typing import List, Union
from .logger import logger

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
    """Encode a uint<M> padded to 256 bits
    :param bits: number of bits <M>
    :param value: either a concrete value, or a Value object
    """
    _check_int_bits(bits)

    if isinstance(value, int):
        if value < 0:
            logger.warning(f"Negative value {value} encoded as uint{bits}")
        elif value >= (1 << bits):
            logger.warning(f"{value} will be truncated to fit in uint{bits}, ")
        return Cst(256, value)
    elif isinstance(value, Value):
        if value.size != bits:
            raise ABIException(
                f"Size mismatch between value size ({value.size}) and uint{bits}"
            )
        if bits < 256:
            return Concat(
                Cst(256 - bits, 0), value
            )  # Zero extend because unsigned
        else:
            return value
    else:
        raise ABIException("'value' must be int or Value")


def selector(func_signature: str) -> Value:
    """Return the first 4 bytes of the keccak256 hash of 'func_signature'"""
    k = sha3.keccak_256()
    k.update(func_signature.encode())
    digest = k.digest()[:4]
    return Cst(32, int.from_bytes(digest, "big"))


def function_call(func: str, args_spec: str, *args) -> List[Value]:
    """Encode a function call
    :param func: the name of the function to call
    :param args_spec: a string describing the type of arguments, e.g '(int256,bytes)' or 'uint'
    """
    # Parse function arguments
    try:
        args_spec = "".join(args_spec.split())  # strip all whitespaces
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
