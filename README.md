# palantir
WORK IN PROGRESS - do not use

## Echidna hybrid fuzzing

- [x] Simple CI with linter
- [x] Simple logger
- [ ] Serialization for transaction data types
- [ ] Coverage APIs
  - [x] per instruction set
  - [ ] per path

- [x] Simple script that takes corpus from echidna, runs it, collects coverage, then tries to discover inputs for new paths based on that
- [x] Implement main script using `EVMWorld` instead of a single `MaatEngine` instance

- [ ] Full echidna integration
  - [ ] Serialize new inputs back into JSON corpus files (issue #3)
  - [ ] Iteratively run echidna with the new inputs and palantir with new corpus cases, until we reach a fixed point, or a number of iterations, or the user stops the process
 
- [ ] Simple PoC that we can increase echidna coverage with SE
  
## MISC

- [ ] Implement `ContractRunner`: execution wrapper for a single contract
  - [x] Load and run a single transaction
  - [ ] Run a series of transactions
  - [x] Handle possible REVERT by using snapshoting
  - [ ] Provide a callback API for events (pass the runner as argument to the callback, everything else is accessible from there)
    - [ ] Pushing new runtime / new transaction
    - [ ] Deleting a runtime / end transaction
  - Handle re-entrency:
    - [x] Hold a stack of `MaatEngine` instances on re-entrency
    - [ ] Automatically make a copy of the top-level engine on re-entrency

- [x] Update `coverage` module to work with a `EVMWorld` (subscribe to events)

- EVMWorld (this class should basically have the same API as MaatEngine so that all exploration algorithms, etc, can work on the whole EVM world seamlessly)
  - [ ] snapshoting interface
  - [ ] serialization interface: maybe have a EVMWorldSerializer class (don't forget to not serialize each engine separately but serialize them in batch to avoid serializing the environment every time)
  - [ ] calls accross contracts & delegate call into same contract