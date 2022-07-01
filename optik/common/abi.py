from ctypes.wintypes import BYTE
from maat import Cst, Concat, Extract, Value
from .exceptions import ABIException
import sha3
from eth_abi.grammar import ABIType, BasicType, TupleType, parse, normalize
from eth_abi.exceptions import ABITypeError, ParseError
from typing import Tuple, List, Union
from .logger import logger
from ..common.util import list_has_types
from dataclasses import dataclass
from maat import contract, MaatEngine, Sext, Var, VarContext

# =========
# Constants
# =========
ADDRESS_SIZE = 160  # Bit size of Ethereum ADDRESS type
BYTEM_PAD = 32  # BytesM padded to 32 bytes
BYTESIZE = 8  # 8 bits to a byte
BOOL_SIZE = 8  # Bit size of Ethereum BOOL type
BOOL_TRUE = 1  # Uint representation of True
BOOL_FALSE = 0  # Uint representation of False

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


def _check_bytes(byteCount: int) -> None:
    """Raise an exception if number of bytes is not within
    the acceptable range"""
    if byteCount <= 0:
        raise ABIException("bytes: can't have fewer than zero bytes")
    if byteCount > 32:
        raise ABIException("bytes: can't have more than 32 bytes")


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
    logger.debug(f"Value is: {value}")
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
        return [Sext(256, value)]
    else:
        return [value]

def addressEnc(
    _: int, value: Union[int, Value], ctx: VarContext, name: str
) -> List[Value]:
    """Encodes an address. Addresses are equivalent to `ADDRESS_SIZE` sized
    unsigned integers, so simply encode as that
    :param _: unneeded variable (required for modularity)
    :param value: either a concrete value, or a Value object
    :param ctx: the VarCOntext to use to make 'value' concolic
    :param name: symbolic variable name to use to make 'value' concolic
    """

    return uintM(ADDRESS_SIZE, value, ctx, name)

def bytesM(
    byte_count: int,
    value: Union[List[int], List[Value]],
    ctx: VarContext,
    name: str,
) -> List[Value]:
    """Encodes a bytes<M>, right-padded to 32 bytes (256 bits)

    :param byteCount: number of bytes "M", 0 < M <= 32
    :param value: either a list of bytes, or a list of Value objects representing bytes
    :param ctx: the VarContext to use to make 'value' concolic
    :param name: symbolic variable name to use to make 'value' concolic

    :return: list of abstract Values to append to transaction data
    """
    _check_bytes(byte_count)

    if list_has_types(value, int):
        for v in value:
            if v < 0:
                raise ABIException(f"byte value {v} must be positive")
            elif v >= 256:
                raise ABIException(
                    f"ABI: byte value {v} greater than 255 overflows"
                )

        values = []
        for i, v in enumerate(value):
            byte_name = f"{name}_{i}"
            ctx.set(byte_name, v, BYTESIZE)
            values += [Var(BYTESIZE, byte_name)]

    elif list_has_types(value, Value):
        for val in value:
            if val.size != BYTESIZE:
                raise ABIException(
                    f"Size mismatch between concolic value ({val.size}) and expected 8 bits of a byte"
                )

        if len(value) != byte_count:
            raise ABIException(
                f"Mismatch between number of concolic bytesM values found {len(value)} and expected {byte_count}."
            )

    else:
        raise ABIException("'value' must be List[int] or List[Value]")

    # pad with 0 bytes to 32 bytes if needed
    if byte_count < 32:
        values += [Cst(BYTESIZE, 0) for _ in range(BYTEM_PAD - byte_count)]

    return values


def boolEnc(
    value: Union[bool, Value], ctx: VarContext, name: str
) -> List[Value]:
    """Encodes a bool type as a uint8 value

    :param value: either a concrete True or False, or a Value object
    :param ctx: the VarContext to use to make 'value' concolic
    :param name: symbolic variable name to use to make 'value' concolic
    """
    if isinstance(value, bool):
        return uintM(
            BOOL_SIZE, BOOL_TRUE if value is True else BOOL_FALSE, ctx, name
        )
    elif isinstance(value, Value):
        return uintM(BOOL_SIZE, value, ctx, name)
    else:
        raise ABIException("'value' must be bool or value")

def tupleEnc(
    ty: ABIType, value: Union[List, Value], ctx: VarContext, name: str
) -> List[Value]:
    """Encodes a dynamically typed and sized tuple (general form of arrays)

    :param ty: ETH Grammar type information about tuple
    :param value: either a tuple of values or a Value object
    :param ctx: the VarContext to use to make 'value' concolic
    :param name: symbolic variable base name to use to make 'value' concolic
    """

    def head(x: ABIType, length: int, name: str) -> List[Value]:
        """As defined in the ABI specification, encodes x

        :param x: the value to encode
        :param length: number of types (for dynamic)
        :param name: name to encode this type as
        """
        res = []
        if x.is_dynamic:
            res += [uintM(256, length, ctx, )]
        else:
            pass

    def tail(x: ABIType, type_name: str) -> List[Value]:
        """As defined in the ABI specification, encodes x
        
        """
        if x.is_dynamic:
            return []
        else:
            return [  ]

    if ty.is_dynamic:
        
        pass
    else:
        # Type is not dynamic and size is not dynamic
        pass
def arrayStatic(
    ty: ABIType, arr: Union[List, Value], ctx: VarContext, name: str
) -> List[Value]:
    """Encodes a static sized list
    
    :param ty: ETH Grammar type information
    :param arr: the array to encode, an array of either concrete or symbolic variables
    :param ctx: the VarCOntext to use to make 'value' concolic
    :param name: symbolic variable name to use to make 'value' concolic
    """

 

    raise NotImplementedError


def arrayDynamic(
    sub: int, arr: Union[List, Value], ctx, VarContext, name: str
) -> List[Value]:
    """Encoded a dynamic array of variables

    :param sub: meta information about the variables
    :param arr: the array to encode, an array of either concrete or symbolic variables
    :param ctx: the VarCOntext to use to make 'value' concolic
    :param name: symbolic variable name to use to make 'value' concolic
    """
    pass


# List of types and their encoder functions
encoder_functions = {
    "uint": uintM,
    "int": intM,
    "address": addressEnc,
    "bool": boolEnc,
    "bytes": bytesM,
    "static_array": arrayStatic,
    "dynamic_array": arrayDynamic
}

def selector(func_signature: str) -> Value:
    """Return the first 4 bytes of the keccak256 hash of 'func_signature'"""
    k = sha3.keccak_256()
    k.update(func_signature.encode())
    digest = k.digest()[:4]
    return Cst(32, int.from_bytes(digest, "big"))

def encode_arguments(arg_components: Tuple[ABIType], ctx: VarContext, tx_name: str, *args) -> List[Value]:
    """Encodes arguments for a function call

    :param arg_components: tupe of ABI types containing their components
    :param ctx: the VarContext to use to make function arguments concolic
    :param tx_name: unique transaction name, used to make symbolic variables

    :returns: list of values
    """

    arg_encodings = []

    logger.debug(f"args: {args}")

    # Encode arguments
    for i, ty in enumerate(arg_components):
        arg_name = f"{tx_name}_arg{i}"

        logger.debug(f"ty type: {type(ty)}, value: {ty}")

        if isinstance(ty, TupleType):
            # type is a tuple
            arg_encodings += tupleEnc(ty, args[i], ctx, arg_name)
            continue

        if ty.is_array:
            if ty.is_dynamic:
                # array with type that is dynamic or dynamic size
                # TODO: add additional check to restrict this to only dynamic size?
                #   - will have to happen
                arg_encodings += arrayDynamic(ty, args[i], ctx, arg_name)
            else:
                # is a static array and has static type
                logger.debug(f"sub: {ty.sub}, args: {args[i]}, ctx: {type(ctx)}, arg_name: {arg_name}")
                arg_encodings += arrayStatic(ty, args[i], ctx, arg_name)
        else:
            # just a bare element
            logger.debug(f"components: {dir(ty)}")

            if not ty.base in encoder_functions:
                logger.debug(f"sub: {ty.sub}, base: {ty.base}, value: {args[i]}")
                raise ABIException(f"Unsupported type: {ty.base}")

            encoder = encoder_functions[ty.base]
            arg_encodings += encoder(ty.sub, args[i], ctx, arg_name)

    return arg_encodings

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
    logger.debug(f"function call args: {args}")
    logger.debug(f"args spec: {args_spec}")
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

    logger.debug(f"args types: {args_types}")
    logger.debug(f"the components: {args_types.components}")
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

    # encode the arguments too
    logger.debug(f"args_types: {args_types}")
    logger.debug(f"args_types components: {args_types.components}")
    res += encode_arguments(args_types.components, ctx, tx_name, *args)

    return res
