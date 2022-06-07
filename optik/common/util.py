from maat import Value


def twos_complement_convert(arg: int, bits: int) -> int:
    """Takes an python integer and determines it's two's complement value
    in a given bit size

    :param arg: argument to
    :param bits: bit length of the two's complement number

    :return: two's complement integer of `bits` length
    """
    bitRepr = format(abs(arg), 'b')
    bitLen = len(bitRepr)

    formatter = "{0:0" + str(bits) + "b}"
    bitstring = formatter.format(arg)

    if bitLen == bits:
        # truncate
        bitstring = bitstring[1:]

    if arg >= 0:
        return int(bitstring, 2)
    else:
        flipped = list(map(lambda b: '1' if b == '0' else '0', bitstring))
        twosCompl = int(flipped, 2) + 1
        return twosCompl
        

        




    