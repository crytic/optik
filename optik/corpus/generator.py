from typing import Any, List, Set
from slither.slither import SlitherCore
from optik.dataflow.dataflow import (
    DataflowGraph,
    DataflowNode,
    get_base_dataflow_graph,
)
import itertools


def all_combinations(choices: Set[Any]) -> List[List[Any]]:
    res = [
        list(x)
        for r in range(1, len(choices) + 1)
        for x in itertools.combinations(choices, r)
    ]
    return res


# TODO make this abstract
class CorpusGenerator:
    """TODO"""

    def __init__(self, contract_name: str, slither: SlitherCore):
        self.dataflow_graph: DataflowGraph = get_base_dataflow_graph(
            contract_name, slither
        )
        self.func_template_mapping: Dict = {}  # TODO(boyan): type hint
        self.current_tx_sequences: List[List[DataflowNode]] = []

    def init_tx_sequences(self) -> None:
        """Create initial set of sequences of 1 transaction each"""
        self.current_tx_sequences = [[n] for n in self.dataflow_graph.nodes]

    def inc_depth(self) -> None:
        """Add one transaction to the current transaction sequences"""
        new_tx_sequences = []
        for tx_seq in self.current_tx_sequences:
            func = tx_seq[0]
            new_tx_sequences += [
                pref + tx_seq for pref in all_combinations(func.parents)
            ]
        self.current_tx_sequences = new_tx_sequences

    def __str__(self):
        res = f"Dataflow graph:\n {self.dataflow_graph}"

        res += "Current tx sequences:\n"
        for i, tx_seq in enumerate(self.current_tx_sequences):
            res += (
                f"{i}: "
                + " -> ".join([node.func.name for node in tx_seq])
                + "\n"
            )

        return res


class EchidnaCorpusGenerator(CorpusGenerator):
    def init_func_template_mapping(self, corpus_dir: str) -> None:
        """Initialize the mapping between functions and their JSON
        serialized Echidna transaction data"""
        raise NotImplementedError()
