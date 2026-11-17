"""Regression test for the Hamming(7,4) codec used in the notebooks.

Exhaustive over single-bit errors: 16 data words x 7 error positions = 112 cases.
A correct Hamming(7,4) recovers every one of them.

Run:  python test_hamming.py
"""


def add_hamming_code(bitstream):
    """4 data bits -> 7 bits, parity at positions 1, 2, 4."""
    encoded = []
    for i in range(0, len(bitstream), 4):
        d = bitstream[i:i + 4].ljust(4, '0')
        p1 = str(int(d[0]) ^ int(d[1]) ^ int(d[3]))
        p2 = str(int(d[0]) ^ int(d[2]) ^ int(d[3]))
        p3 = str(int(d[1]) ^ int(d[2]) ^ int(d[3]))
        encoded.append(p1 + p2 + d[0] + p3 + d[1] + d[2] + d[3])
    return ''.join(encoded)


def detect_and_correct_hamming(encoded_bitstream, _reversed=False):
    """Locate and flip the single erroneous bit in each 7-bit block.

    `_reversed=True` reproduces the original bug (syndrome assembled s1 s2 s3)
    and exists only so the test can show the difference.
    """
    corrected, errors = [], []
    for i in range(0, len(encoded_bitstream), 7):
        block = encoded_bitstream[i:i + 7]
        if len(block) < 7:
            corrected.append(block)
            continue
        p1, p2, d1, p3, d2, d3, d4 = block
        s1 = str(int(p1) ^ int(d1) ^ int(d2) ^ int(d4))   # checks position 1
        s2 = str(int(p2) ^ int(d1) ^ int(d3) ^ int(d4))   # checks position 2
        s3 = str(int(p3) ^ int(d2) ^ int(d3) ^ int(d4))   # checks position 4
        # Parity sits at positions 1, 2, 4, so the position-1 check is the LEAST
        # significant syndrome bit: the order is s3 s2 s1.
        syndrome = (s1 + s2 + s3) if _reversed else (s3 + s2 + s1)
        pos = int(syndrome, 2) - 1
        if pos >= 0:
            block = list(block)
            block[pos] = '0' if block[pos] == '1' else '1'
            errors.append(i + pos)
            block = ''.join(block)
        corrected.append(block)
    return ''.join(corrected), errors


def remove_hamming_code(e):
    """Strip parity, returning the 4 data bits per 7-bit block."""
    return ''.join(e[i + 2] + e[i + 4] + e[i + 5] + e[i + 6]
                   for i in range(0, len(e), 7))


def _sweep(reversed_order):
    recovered, failures = 0, {}
    for v in range(16):
        data = format(v, '04b')
        clean = add_hamming_code(data)
        for p in range(7):
            corrupt = list(clean)
            corrupt[p] = '0' if corrupt[p] == '1' else '1'
            fixed, _ = detect_and_correct_hamming(''.join(corrupt), reversed_order)
            if remove_hamming_code(fixed) == data:
                recovered += 1
            else:
                failures[p + 1] = failures.get(p + 1, 0) + 1
    return recovered, failures


def demo():
    total = 112
    ok, fails = _sweep(reversed_order=False)
    bad_ok, bad_fails = _sweep(reversed_order=True)

    print(f"single-bit error cases : {total}  (16 data words x 7 positions)")
    print(f"current implementation : {ok}/{total} recovered ({100 * ok / total:.1f}%)")
    print(f"original bit ordering  : {bad_ok}/{total} recovered ({100 * bad_ok / total:.1f}%)")
    if bad_fails:
        print("\nthe original ordering failed at bit positions:")
        for p in sorted(bad_fails):
            print(f"   position {p}: {bad_fails[p]}/16 data words")

    assert ok == total, f"Hamming decoder regressed: only {ok}/{total} recovered"
    assert not fails, f"unexpected failures at {sorted(fails)}"
    assert bad_ok == 80, "the buggy ordering should recover exactly 80/112"
    print("\nOK: single-bit errors are fully corrected.")


if __name__ == "__main__":
    demo()
