from ctypes.wintypes import BYTE
from maat import Cst, Concat, Extract, Value
from .exceptions import ABIException
import sha3
from functools import reduce
from itertools import accumulate
from eth_abi.grammar import ABIType, BasicType, TupleType, parse, normalize
from eth_abi.exceptions import ABITypeError, ParseError
from typing import Tuple, List, Union, Any
from .logger import logger
from ..common.util import list_has_types
from dataclasses import dataclass
from maat import Sext, Var, VarContext

# =========
# Constants
# =========
ADDRESS_SIZE = 160  # Bit size of Ethereum ADDRESS type
BASE_HEAD_SIZE = 32  # Elementary types have 32 byte sized heads
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


def address_enc(
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


def bool_enc(
    _, value: Union[bool, Value], ctx: VarContext, name: str
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


def compute_head_lengths(ty: ABIType) -> int:
    """Determine byte length of heads of types contained in `ty`

    :param ty: the type to compute head lengths over
    """

    if isinstance(ty, TupleType) and not ty.is_dynamic:
        # if non-dynamic tuple, encoded in place
        return sum([compute_head_lengths(t) for t in ty.components])

    if ty.is_dynamic:
        # all dynamic types are referenced by an offset, which is encoded as a uint
        return BASE_HEAD_SIZE

    if ty.is_array:
        # static array, so has static type and static size
        dimensions = ty.arrlist
        # compute total size of matrix
        size = reduce(lambda a, b: a * b, [dim[0] for dim in dimensions])

        return size * BASE_HEAD_SIZE

    # is an elementary type
    return BASE_HEAD_SIZE


def tuple_enc(
    tup: TupleType,
    values: Union[List, Value],
    ctx: VarContext,
    name: str,
    is_top: bool = False,
) -> List[Value]:
    """Encodes a dynamically typed and sized tuple (general form of arrays)

    :param ty: ETH Grammar type information about tuple
    :param values: Either a tuple of values or a Value object
    :param ctx: The VarContext to use to make 'value' concolic
    :param name: Symbolic variable base name to use to make 'value' concolic
    :param is_top: True if this tuple is function arguments, False otherwise
    """

    base_head_length = compute_head_lengths(tup)
    cum_tail_length = 0

    def head(x: ABIType, value, ctx: VarContext, base_name: str) -> List[Value]:
        """As defined in the ABI specification, encodes head(x)

        :param x: type to encode
        :param value: concrete value to encode
        :param ctx: the VarContext to use to make 'value' concolic
        :param base_name: name to build upon for use as a symbolic variable name
        """
        if x.is_dynamic:
            # head(X(i)) = enc(len( head(X(1) ... X(k) tail(X(1)) ... tail(X(i-1))) ))
            offset = base_head_length + cum_tail_length
            return [Cst(256, offset)]
        else:
            v = encode_value(x, value, ctx, base_name)
            return v

    def tail(x: ABIType, value, ctx: VarContext, base_name: str) -> List[Value]:
        """As defined in the ABI specification, encodes tail(x)

        :param x: type to encode
        :param value: concrete value to encode
        :param ctx: the VarContext to use to make 'value' concolic
        :param base_name: name to build upon for use as a symbolic variable name
        """
        if x.is_dynamic:
            v = encode_value(x, value, ctx, base_name)
            return v
        else:
            return []

    def tail_length(tail: List[Value]) -> int:
        """Finds size of the tail in bytes

        :param tail: Tail of values
        """

        # number of bits in the tail
        size = sum([val.size for val in tail])

        # 8 bits to a byte
        return size / 8

    heads = []
    tails = []

    for i, ty in enumerate(tup.components):
        if is_top:
            arg_name = f"{name}_arg{i}"
        else:
            arg_name = f"{name}_{i}"

        # compute encodings
        ty_head = head(ty, values[i], ctx, arg_name)
        ty_tail = tail(ty, values[i], ctx, arg_name)

        # increase data section (tail)
        cum_tail_length += tail_length(ty_tail)

        heads += ty_head
        tails += ty_tail

    # not a coin toss
    return heads + tails


def array_fixed(
    ty: ABIType, arr: Union[List, Value], ctx: VarContext, name: str
) -> List[Value]:
    """Encodes a statically sized array of values

    :param ty: type information for array
    :param arr: the array to encode, an array of either concrete or symbolic variables
    :param ctx: the VarCOntext to use to make 'value' concolic
    :param name: symbolic variable name to use to make 'value' concolic
    """

    # fixed sized arrays encoded as tuple of elements with constant type
    el_type = ty.item_type.to_type_str()
    tup_descriptor = "(" + ",".join([el_type for _ in range(len(arr))]) + ")"
    tup_type = parse(tup_descriptor)

    return tuple_enc(tup_type, arr, ctx, name)


def array_dynamic(
    ty: ABIType, arr: Union[List, Value], ctx: VarContext, name: str
) -> List[Value]:
    """Encoded a dynamically sized array of values

    :param ty: type information for array
    :param arr: the array to encode, an array of either concrete or symbolic variables
    :param ctx: the VarCOntext to use to make 'value' concolic
    :param name: symbolic variable name to use to make 'value' concolic
    """

    el_count = len(arr)
    # encode number of elements as a constant
    # TODO: support variable length arrays up for debate
    k_enc = [Cst(256, el_count)]

    # dynamic size array encoded as concatenation of: enc(len(X)) + enc(X)
    return k_enc + array_fixed(ty, arr, ctx, name)


# List of elementary types and their encoder functions
encoder_functions = {
    "uint": uintM,
    "int": intM,
    "address": address_enc,
    "bool": bool_enc,
    "bytes": bytesM,
}


def selector(func_signature: str) -> Value:
    """Return the first 4 bytes of the keccak256 hash of 'func_signature'"""
    k = sha3.keccak_256()
    k.update(func_signature.encode())
    digest = k.digest()[:4]
    return Cst(32, int.from_bytes(digest, "big"))


def encode_value(
    ty: ABIType, value: Any, ctx: VarContext, arg_name: str
) -> List[Value]:
    """ABI encode a value of type `ty`

    :param ty: type of the value
    :param value: value to encode
    :param ctx: The VarContext to use to make 'value' concolic
    :param name: symbolic variable name to use to make 'value' concolic
    """
    if isinstance(ty, TupleType):
        # type is a tuple
        return tuple_enc(ty, value, ctx, arg_name)

    if ty.is_array:
        if ty._has_dynamic_arrlist:
            # array is dynamically sized
            return array_dynamic(ty, value, ctx, arg_name)
        else:
            # is a static sized array
            return array_fixed(ty, value, ctx, arg_name)
    else:
        # elementary type
        if not ty.base in encoder_functions:
            raise ABIException(f"Unsupported type: {ty.base}")

        encoder = encoder_functions[ty.base]
        return encoder(ty.sub, value, ctx, arg_name)


def encode_arguments(
    ty: TupleType, ctx: VarContext, tx_name: str, *args
) -> List[Value]:
    """Encodes arguments for a function call

    :param arg_components: tuple of ABI types containing their components
    :param ctx: the VarContext to use to make function arguments concolic
    :param tx_name: unique transaction name, used to make symbolic variables

    :returns: list of values
    """
    # function arguments are encoded as a tuple
    return tuple_enc(ty, args, ctx, tx_name, is_top=True)


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

    # encode the arguments too
    res += encode_arguments(args_types, ctx, tx_name, *args)

    def pprint_encoding() -> str:
        """Formats `res` into a hexadecimal view of the encoding"""

        cum_bit_sizes = list(accumulate([v.size for v in res[1:]]))
        res_sizes = list(zip(cum_bit_sizes, res[1:]))

        return "0x" + "".join(
            [
                f"{v.as_uint(ctx):02x}".zfill(64)
                for size, v in res_sizes
                if size % 256 == 0
            ]
        )

    logger.debug(f"Selector: {'0x' + str(res[0])[2:].zfill(48)}")
    logger.debug(f"Argument  encoding: {pprint_encoding()}")
    return res
