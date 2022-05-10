from maat import contract, MaatEngine, Var


def symbolicate_tx_data(m: MaatEngine) -> None:
    """Make transaction data symbolic for an engine.

    Each concrete value in the transaction data buffer (except the function selector)
    is made concolic.

    Prerequisite: a transaction MUST already be set in the contract associated with the
    engine
    """
    tx_data = contract(m).transaction.data
    if not tx_data:
        raise GenericException("Transaction data empty")
    res = [tx_data[0]]  # Don't make selector symbolic
    # Symbolicate every argument if not already symbolic
    for i, val in enumerate(tx_data[1:]):
        if val.is_concrete(m.vars):
            varname = f"arg{i}"
            res.append(Var(val.size, varname))
            m.vars.set(varname, val.as_uint(), val.size)
        else:
            # Value already symbolic, don't change it
            res.append(val)
    # Assign new tx data
    contract(m).transaction.data = res
