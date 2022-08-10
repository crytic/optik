from typing import List, Optional, Set

from slither.core.declarations.function import Function
from slither.printers.guidance.echidna import _extract_function_relations
from slither.slither import SlitherCore

from ..common.exceptions import DataflowException


class DataflowNode:
    """A node representing a function in a DataflowGraph

    Attributes:
        func: the function represented by the node
        children: functions that use data modified by this function
        parents: functions that modify data used by this function
    """

    def __init__(self, func: Function):
        self.func = func
        self.children: Set[DataflowNode] = set()
        self.parents: Set[DataflowNode] = set()

    def __str__(self) -> str:
        res = f"{self.func.name}:"
        res += f"\tImpacts: {', '.join([c.func.name for c in self.children])}"
        res += (
            f"\tImpacted by: {', '.join([p.func.name for p in self.parents])}"
        )
        return res


class DataflowGraph:
    """A graph representing use-def dataflow chains between functions

    Attributes:
        nodes: all functions present in the dataflow graph
    """

    def __init__(self) -> None:
        self.nodes: List[DataflowNode] = []

    def add_function(self, func: Function) -> None:
        """Add a node for function 'func'. If the function is already
        present in the graph, does nothing"""
        if any(x.func is func for x in self.nodes):
            return
        self.nodes.append(DataflowNode(func))

    def get_node(self, func: Function) -> Optional[DataflowNode]:
        """Returns the node corresponding to function 'func', or None
        if no such node exists"""
        for n in self.nodes:
            if n.func is func:
                return n
        return None

    def add_dataflow(self, src: Function, dst: Function) -> None:
        """Add a dataflow dependency between two functions

        :param src: function that modifies data used by 'dst'
        :param dst: function that uses data modified by 'src'
        """
        s = self.get_node(src)
        d = self.get_node(dst)
        if s and d:
            s.children.add(d)
            d.parents.add(s)

    def __str__(self) -> str:
        return "\n".join([str(n) for n in self.nodes])


def ignore_func(func: Function) -> bool:
    """Returns True if the function must not be included in a
    dataflow graph. This includes:
        - constructors
        - private or internal functions
    """
    return func.is_constructor or func.visibility not in [
        "public",
        "external",
    ]


def get_base_dataflow_graph(
    contract_name: str, slither: SlitherCore
) -> DataflowGraph:
    """Use slither to return the basic dataflow graph for a given contract

    :param contract_name: the contract for which to build the graph
    :slither: the SlitherCore object analyzing the file containing the
        target contract
    """
    res = DataflowGraph()
    rels = _extract_function_relations(slither)
    rels = rels[contract_name]  # TODO KeyError

    contracts = slither.get_contract_from_name(contract_name)
    if len(contracts) > 1:
        raise DataflowException(
            f"More than one contract named '{contract_name}'"
        )
    if not contracts:
        raise DataflowException(f"No contract named '{contract_name}'")
    contract = contracts[0]

    # Add functions to the dataflow graph
    for func, deps in rels.items():
        # Add all function dependencies
        func = contract.get_function_from_signature(func)
        if ignore_func(func):
            continue
        res.add_function(func)
        for dst in deps["impacts"]:
            dst = contract.get_function_from_signature(dst)
            if dst is None or ignore_func(dst):
                continue
            res.add_function(dst)
            res.add_dataflow(func, dst)
        for src in deps["is_impacted_by"]:
            src = contract.get_function_from_signature(src)
            if src is None or ignore_func(src):
                continue
            res.add_function(src)
            res.add_dataflow(src, func)

    return res
