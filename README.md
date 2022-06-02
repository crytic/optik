# Optik
WORK IN PROGRESS - do not use yet for real audits

## Echidna hybrid fuzzing
Example usage: `hybrid-echidna ExploreMe.sol  --test-mode assertion --corpus-dir /tmp/test7 --seq-len 1`

Help: `hybrid-echidna -h`

Limitations:
- Can only run on a single solidity file
- Can't deploy multiple contracts
- No re-entrency

TODO:
- [x] Simple CI with linter
- [x] Simple logger
- [ ] Serialization for all transaction data types (https://solidity-fr.readthedocs.io/fr/latest/abi-spec.html)
  - [ ] `int<M>`
  - [ ] `address`
  - [ ] `bool`
  - [ ] `fixed<M>x<N>`
  - [ ] `ufixed<M>x<N>`
  - [ ] `bytes<M>`
  - [ ] `function`
  - [ ] `<type>[M]`: fixed-length array
  - [ ] `bytes`: dynamic sized byte sequence
  - [ ] `string`: dynamic sized unicode string assumed to be UTF-8 encoded
  - [ ] `<type>[]`: variable-length array
  - [ ] `tuple`

- [ ] Coverage APIs
  - [x] per instruction set
  - [ ] per path

- [x] Simple script that takes corpus from echidna, runs it, collects coverage, then tries to discover inputs for new paths based on that
- [x] Implement main script using `EVMWorld` instead of a single `MaatEngine` instance

- [x] Full echidna integration
  - [ ] Support more echidna command line arguments
  - [x] Serialize new inputs back into JSON corpus files (issue #3)
  - [x] Iteratively run echidna with the new inputs and Optik with new corpus cases, until we reach a fixed point, or a number of iterations, or the user stops the process
 
- [x] Simple PoC that we can increase echidna coverage with SE
  
## MISC

- [ ] Implement `ContractRunner`: execution wrapper for a single contract
  - [x] Load and run a single transaction
  - [ ] Run a series of transactions
  - [x] Handle possible REVERT by using snapshoting
  - Handle re-entrency:
    - [x] Hold a stack of `MaatEngine` instances on re-entrency
    - [ ] Automatically make a copy of the top-level engine on re-entrency

- [x] Update `coverage` module to work with a `EVMWorld` (subscribe to events)

- EVMWorld (this class should basically have the same API as MaatEngine so that all exploration algorithms, etc, can work on the whole EVM world seamlessly)
  - [ ] snapshoting interface
  - [ ] serialization interface: maybe have a EVMWorldSerializer class (don't forget to not serialize each engine separately but serialize them in batch to avoid serializing the environment every time)
  - [ ] calls accross contracts & delegate call into same contract
  - [x] Provide a callback API for events (`WorldMonitor`)
