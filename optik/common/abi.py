from maat import Cst, Concat, Extract, Value
from .exceptions import ABIException
import sha3
from eth_abi.grammar import ABIType, BasicType, TupleType, parse, normalize
from eth_abi.exceptions import ABITypeError, ParseError
from typing import List, Union
from .logger import logger
from dataclasses import dataclass
from maat import contract, MaatEngine, Var, VarContext

# =========
# Constants
# =========
ADDRESS_SIZE = 160  # Bit size of Ethereum ADDRESS type

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


def uintM(
    bits: int, value: Union[int, Value], ctx: VarContext, name: str
) -> List[Value]:
    """Encode a uint<M> padded to 256 bits

    :param bits: number of bits <M>
    :param value: either a concrete value, or a Value object
    :param ctx: the VarContext to use to make 'value' concolic
    :param name: symbolic variable name to use to make 'value' concolic

    :return: a list of abstract Values to append to the transaction data
    """
    _check_int_bits(bits)
    # Sanity checks
    if isinstance(value, int):
        if value < 0:
            logger.warning(f"Negative value {value} encoded as uint{bits}")
        elif value >= (1 << bits):
            logger.warning(f"{value} will be truncated to fit in uint{bits}, ")
        # TODO(boyan): raise exception if 'name' already present in 'ctx' ?
        ctx.set(name, value, bits)  # Set concolic value in context
        value = Var(bits, name)  # Make value concolic
    elif isinstance(value, Value):
        if value.size != bits:
            raise ABIException(
                f"Size mismatch between value size ({value.size}) and uint{bits}"
            )
    else:
        raise ABIException("'value' must be int or Value")
    # Return tx data
    if bits < 256:
        return [
            Cst(256 - bits, 0),  # zero padding (zero because unsigned)
            value,  # value on 'M' bits
        ]
    else:
        return [value]


def intM(
    bits: int, value: Union[int, Value], ctx: VarContext, name: str
) -> List[Value]:
    """Encodes a int<M> (signed 2's complement) padded to 256 bits

    :param bits: number of bits <M>
    :param value: either a concrete value, or a Value object
    :param ctx: the VarContext to use to make 'value' concolic
    :param name: symbolic variable name to use to make 'value' concolic

    :return: list of abstract Values to append to the transaction data
    """
    _check_int_bits(bits)
    # Sanity check
    if isinstance(value, int):
        # Signed 2's complement bounds
        upperBound = (1 << (bits - 1)) - 1
        lowerBound = -(1 << (bits - 1))
        if value > upperBound or value < lowerBound:
            logger.warning(
                f"Signed integer value {value} outside bounds permitted by {bits} bits"
            )
        ctx.set(name, value, bits)
        value = Var(bits, name)
    elif isinstance(value, Value):
        if value.size != bits:
            raise ABIException(
                f"Size mismatch between value size ({value.size}) and int{bits}"
            )
    else:
        raise ABIException("'value' must be int or Value")

    if bits < 256:
        return [Cst(256 - bits, 0), value]
    else:
        return [value]


def selector(func_signature: str) -> Value:
    """Return the first 4 bytes of the keccak256 hash of 'func_signature'"""
    k = sha3.keccak_256()
    k.update(func_signature.encode())
    digest = k.digest()[:4]
    return Cst(32, int.from_bytes(digest, "big"))


def function_call(
    func: str, args_spec: str, ctx: VarContext, tx_name: str, *args
) -> List[Value]:
    """Encode a function call

    :param func: the name of the function to call
    :param args_spec: a string describing the type of arguments, e.g '(int256,bytes)' or 'uint'
    :param ctx: the VarContext to use to make function arguments concolic
    :param tx_name: unique transaction name, used to name symbolic variables
        created for function arguments. Can be empty.
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
        arg_name = f"{tx_name}_arg{i}"
        if ty.base == "uint":
            res += uintM(ty.sub, args[i], ctx, arg_name)
        elif ty.base == "int":
            res += intM(ty.sub, args[i], ctx, arg_name)
        elif ty.base == "address":
            res += uintM(ADDRESS_SIZE, args[i], ctx, arg_name)
        else:
            raise ABIException(f"Unsupported type: {ty.base}")

    return res
