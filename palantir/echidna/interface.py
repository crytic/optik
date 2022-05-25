import json
from maat import Cst, EVMTransaction, Value
from typing import Dict, List, Tuple, Union
from ..common.exceptions import EchidnaException
from ..common.abi import function_call
from ..common.logger import logger


def translate_argument(arg: Dict) -> Tuple[str, Union[bytes, int, Value]]:
    """Translate a parsed Echidna transaction argument into a '(type, value)' tuple.
    :param arg: Transaction argument parsed as a json dict"""
    if arg["tag"] == "AbiUInt":
        bits = arg["contents"][0]
        val = int(arg["contents"][1])
        return (
            f"uint{bits}",
            val,
        )
    else:
        raise EchidnaException(f"Unsupported argument type: {arg['tag']}")


def load_tx(tx: Dict) -> EVMTransaction:
    """Translates a parsed echidna transaction into a Maat transaction
    :param tx: Echidna transaction parsed as a json dict"""

    # Translate function call and argument types and values
    call = tx["_call"]
    if call["tag"] != "SolCall":
        raise EchidnaException(f"Unsupported transaction type: '{call['tag']}'")

    arg_types = []
    arg_values = []
    func_name = call["contents"][0]
    if len(call["contents"]) > 1:
        for arg in call["contents"][1]:
            t, val = translate_argument(arg)
            arg_types.append(t)
            arg_values.append(val)

    func_signature = f"({','.join(arg_types)})"
    call_data = function_call(func_name, func_signature, *arg_values)

    # Build transaction
    # TODO: correctly handle all the fields other than 'data'
    # TODO: make EVMTransaction accept integers as arguments
    sender = Cst(256, 1)
    value = Cst(256, 0)
    gas_limit = Cst(256, 46546514651)
    return EVMTransaction(
        sender,  # origin
        sender,  # sender
        2,  # recipient
        value,  # value
        call_data,  # data
        gas_limit,  # gas_limit
    )


def load_tx_sequence(filename: str) -> List[EVMTransaction]:
    """Load a sequence of transactions from an Echidna corpus file
    :param filename: corpus file to load
    """
    with open(filename, "rb") as f:
        data = json.loads(f.read())
        return [load_tx(tx) for tx in data]
