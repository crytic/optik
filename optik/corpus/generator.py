import os
import json
from typing import Any, List, Set, Dict, Final, Optional
from slither.slither import SlitherCore
from ..common.abi import func_signature
from ..echidna.interface import (
    extract_func_from_call,
    get_available_filename,
)
from ..dataflow.dataflow import (
    DataflowGraph,
    DataflowNode,
    get_base_dataflow_graph,
)

from ..common.exceptions import CorpusException
from ..common.logger import logger

# Prefix for files containing seed corpus
SEED_CORPUS_PREFIX: Final[str] = "optik_corpus"

# TODO: remove?
# import itertools
# def all_combinations(choices: Set[Any]) -> List[List[Any]]:
#     res = [
#         list(x)
#         for r in range(1, len(choices) + 1)
#         for x in itertools.combinations(choices, r)
#     ]
#     return res


class CorpusGenerator:
    """Abstract class for fuzzing corpus generation based on dataflow analysis
    with slither"""

    def __init__(self, contract_name: str, slither: SlitherCore):
        self.dataflow_graph: DataflowGraph = get_base_dataflow_graph(
            contract_name, slither
        )
        self.func_template_mapping: Dict[str, DataflowNode] = {}
        self.current_tx_sequences: List[List[DataflowNode]] = []
        # Initialize basic set of 1-tx sequences
        self._init()

    def _init(self) -> None:
        """Create initial set of sequences of 1 transaction each"""
        self.current_tx_sequences = [[n] for n in self.dataflow_graph.nodes]

    @property
    def current_seq_len(self):
        return (
            0
            if not self.current_tx_sequences
            else len(self.current_tx_sequences[0])
        )

    def _step(self) -> None:
        """Update the current transaction sequences by prepending one call
        to all sequences. If multiple calls impact a sequence, create as many
        new sequences as there are such calls"""
        new_tx_sequences = []
        for tx_seq in self.current_tx_sequences:
            # Get all txs that can impact this sequence
            impacts_seq = set().union(*[n.parents for n in tx_seq])
            func = tx_seq[0]
            # Prepend impacting tx(s) to sequence
            new_tx_sequences += [[prev] + tx_seq for prev in impacts_seq]
        self.current_tx_sequences = new_tx_sequences

    def step(self, n=1) -> None:
        for _ in range(n):
            self._step()

    def dump_tx_sequences(self, corpus_dir: str) -> None:
        """Dump the current dataflow tx sequences in new corpus input files"""
        raise NotImplementedError()

    def __str__(self):
        res = f"Dataflow graph:\n {self.dataflow_graph}\n"

        res += "Current tx sequences:\n"
        for i, tx_seq in enumerate(self.current_tx_sequences):
            res += (
                f"{i}: "
                + " -> ".join([node.func.name for node in tx_seq])
                + "\n"
            )

        return res


class EchidnaCorpusGenerator(CorpusGenerator):
    """Corpus generator for Echidna"""

    def init_func_template_mapping(self, corpus_dir: str) -> None:
        """Initialize the mapping between functions and their JSON
        serialized Echidna transaction data. This needs to be called
        before we can dump tx sequences into new inputs

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

    def _dump_tx_sequence(
        self, seq: List[DataflowNode], corpus_dir: str
    ) -> None:
        """Write list of transaction sequences to corpus in Echidna's format

        :param sequence: List of sequential data flow nodes (functions)
        :param corpus_dir: Corpus directory where to write new inputs
        """
        seed = []
        # Retrieve Echidna tx for each function
        for node in seq:
            try:
                seed.append(self.func_template_mapping[node.func.full_name])
            except KeyError:
                raise CorpusException(
                    f"No template for function {node.func.full_name}"
                )

        new_file = get_available_filename(
            f"{corpus_dir}/{SEED_CORPUS_PREFIX}", ".txt"
        )
        # Write seed input in corpus
        logger.debug(f"Adding new corpus seed in {new_file}")
        with open(new_file, "w") as f:
            json.dump(seed, f)

    def dump_tx_sequences(self, corpus_dir: str) -> None:
        """Dump the current dataflow tx sequences in new corpus input files"""
        for seq in self.current_tx_sequences:
            self._dump_tx_sequence(seq, corpus_dir)


def infer_previous_incremental_threshold(corpus_dir: str) -> Optional[int]:
    """Read an Echidna corpus directory and looks for seed files that would
    have been previously generated by Optik. If such files exist, return
    the longest transaction sequence length present in the files"""
    if not os.path.exists(corpus_dir):
        return None

    res = 0
    logger.debug(
        f"Infering previous incremental threshold from corpus dir {corpus_dir}"
    )
    for filename in reversed(list(os.listdir(corpus_dir))):
        if not filename.startswith(SEED_CORPUS_PREFIX):
            continue

        with open(os.path.join(corpus_dir, filename), "rb") as f:
            data = json.loads(f.read())
            res = max(res, len(data))

    return res
