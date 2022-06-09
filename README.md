# Optik
**WORK IN PROGRESS - do not use yet for real audits**

**Optik** is a set of tools based on symbolic execution that provide
assistance during smart-contract audits.

- [Installation](#installation)
- [Hybrid Echidna](#hybrid-echidna)

## Installation

### Dev install
Installation currently doesn't work with `pip` because we need a locally built `pymaat` package which supports EVM, and Maat doesn't have a release on `PyPI` with EVM support yet. So install the dependencies and then run:

```
python3 setup.py install --force 
```

### User install

**Warning: this won't work until we publish an official Maat release with EVM support**

> We plan on publishing a `PyPI` package for `pip` installation when Optik becomes more stable.
> For now you can install it by running:
> 
> ```
> git clone https://github.com/trailofbits/optik && cd optik
> python3 -m pip install .
> ```

## Hybrid Echidna
Optik allows to run the [Echidna](https://github.com/crytic/echidna) smart-contract fuzzer in _hybrid_ mode. It basically couples Echidna with a symbolic executor that replays the Echidna corpus and extends it with new inputs that increase coverage. Attained coverage is computed incrementally for the whole `hybrid-echidna` run, accross multiple fuzzing campaign iterations.

**Usage**:

Hybrid echidna can be used seamlessly in place of regular Echidna by replacing `echidna-test` with `hybrid-echidna` in your Echidna command line. 
For example: 

```
hybrid-echidna MyContract.sol  --test-mode assertion --corpus-dir /tmp/test
```

A couple additionnal options are available:

- `--cov-mode`: type of coverage to increase when solving new inputs. . This option has a significant impact on results and performance, as detailed below:

  - `inst`: reach code/instructions that have never been executed yet

  - `inst-ctx`: same as `inst` but sensitive to the current transaction number. Let's assume a sequence of 2 transactions `[tx0,tx1]` and some solidity statement `A` in the contract's code: even if there is an input in which `A` is executed by `tx0`, Optik will still try to find inputs where `A` is executed by `tx1` if possible. <br><br> 
    <i>Compared to `inst`, `inst-ctx` detects more potential branches in the code. It is thus more likely to discover new inputs, but also puts more load of the symbolic executor</i>
  
  - `path`: reach new execution paths. An execution path is the ordered list of all branches taken when running an input and that directly depend on the input. There is often a quasi-infinite number of possible paths for a contract, so using this coverage mode will generate much more inputs that instruction-base coverage modes. While solving many paths can become a performance bottleneck, it also allows to find deeper bugs in statefull contracts. <br><br>
    <i>We recommend using `path` with a reduced sequence length for fuzzing inputs. For example start with `--seq-len 10` and either increase the number of transactions if `hybrid-echidna` terminates quickly enough, or decrease it if it gets stuck on solving too many inputs</i>
  
  - `path-relaxed`: similar to `path` except that we don't try to reach paths that are sub-paths of bigger paths that we already covered. A given path `P1` is considered a _sub-path_ of path `P2` if all branches of `P1` appear in `P2` in the same order (but not necessarily contiguously). For example, **[3,1,2]** would be a sub-path of [4,**`3,1,2`**], but also of [**`3`**,4,**`1`**,3,**`2`**,4]. <br><br> 
     <i>While `path-relaxed` stays significantly more computational-heavy than instruction-based coverage modes, it is likely to generate less cases than `path`, while still providing good semantic coverage of the target</i>

- `--max-iters`: maxium number of fuzzing iterations to perform (one iteration is one Echidna campaign + one symbolic executor run on the corpus)


**Current limitations**:

- Can only run on a single solidity file
- Can't deploy multiple contracts
- No re-entrency or calls accross contracts
- Gas is taken into account
- Some echidna options are not yet supported (see `hybrid-echidna -h`)
