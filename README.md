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

- [ ] Full echidna integration
  - [ ] Serialize new inputs back into JSON corpus files (issue #3)
  - [ ] Iteratively run echidna with the new inputs and palantir with new corpus cases, until we reach a fixed point, or a number of iterations, or the user stops the process
 
- [ ] Simple PoC that we can increase echidna coverage with SE
  
## MISC

- [ ] Implement `ContractRunner`: execution wrapper for a single contract
  - [ ] Load and run a single transaction
  - [ ] Run a series of transactions
  - [ ] Handle possible REVERT by using snapshoting 
  - Handle re-entrency:
    - [ ] Hold a stack of `MaatEngine` instances on re-entrency
    - [ ] Automatically make a copy of the top-level engine on re-entrency