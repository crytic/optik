import os
import json
from typing import Any, List, Set, Dict, Final
from slither.slither import SlitherCore
from optik.common.abi import func_signature
from optik.echidna.interface import (
    extract_func_from_call,
    get_available_filename,
)
from optik.dataflow.dataflow import (
    DataflowGraph,
    DataflowNode,
    get_base_dataflow_graph,
)
import itertools

# Prefix for files containing seed corpus
SEED_CORPUS_PREFIX: Final[str] = "optik_seed_corpus"


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
        serialized Echidna transaction data

        :param corpus_dir: Corpus directory
        """
        for filename in os.listdir(corpus_dir):
            with open(os.path.join(corpus_dir, filename), "rb") as f:
                data = json.loads(f.read())
                for tx in data:
                    func_name, args_spec, _ = extract_func_from_call(
                        tx["_call"]
                    )
                    func_prototype = func_signature(func_name, args_spec)
                    # Only store one tx for each function
                    if func_prototype in self.func_template_mapping:
                        continue
                    self.func_template_mapping[func_prototype] = tx

    def write_tx_seqs_to_corupus(
        self, sequence: List[List[DataflowNode]], corpus_dir: str
    ):
        """Write list of transaction sequences to corpus in Echidna's format

        :param sequence: List of sequential data flow nodes
        :param corpus_dir: Corpus directory
        """
        for seq in sequence:
            seed = []
            # Retrieve Echidna tx for each function
            for node in seq:
                print(node.func.full_name)
                seed.append(
                    self.func_template_mapping[node.func.full_name]
                )  # (TODO) KeyError

            new_file = get_available_filename(
                f"{os.path.dirname(corpus_dir)}/{SEED_CORPUS_PREFIX}", ".txt"
            )
            # Write seed corpus
            with open(new_file, "w") as f:
                json.dump(seed, f)

    def generate_seed_corpus(self) -> None:
        """Load Echidna transactions, find dataflow relations,
        write new sequences to corpus
        """
        self.init_func_template_mapping("corpus/coverage/")
        self.init_tx_sequences()
        self.write_tx_seqs_to_corupus(
            self.current_tx_sequences, "corpus/coverage/"
        )
