"""Pure-python keccak-256, so event topics are computed rather than recalled.

hashlib ships SHA3, which is NIST-padded and gives different digests from
the Keccak that Ethereum uses. Self-tested below against the canonical
ERC-20 Transfer topic.
"""
_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
M = (1 << 64) - 1


def _rotl(x, n):
    return ((x << n) | (x >> (64 - n))) & M


def _keccak_f(a):
    for rnd in range(24):
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rotl(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                a[x][y] ^= d[x]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rotl(a[x][y], _ROT[x][y])
        for x in range(5):
            for y in range(5):
                a[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y] & M) & b[(x + 2) % 5][y])
        a[0][0] ^= _RC[rnd]
    return a


def keccak256(data: bytes) -> bytes:
    rate = 136
    padded = bytearray(data) + b"\x01" + b"\x00" * ((-len(data) - 1) % rate)
    padded[-1] ^= 0x80
    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(padded), rate):
        blk = padded[off:off + rate]
        for i in range(rate // 8):
            x, y = i % 5, i // 5
            a[x][y] ^= int.from_bytes(blk[i * 8:(i + 1) * 8], "little")
        a = _keccak_f(a)
    out = b""
    for i in range(4):
        x, y = i % 5, i // 5
        out += a[x][y].to_bytes(8, "little")
    return out[:32]


def topic(sig: str) -> str:
    return "0x" + keccak256(sig.encode()).hex()


if __name__ == "__main__":
    known = {
        "Transfer(address,address,uint256)":
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
        "Swap(address,uint256,uint256,uint256,uint256,address)":
            "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822",
        "PairCreated(address,address,address,uint256)":
            "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9",
    }
    ok = True
    for sig, want in known.items():
        got = topic(sig)
        flag = "ok" if got == want else "MISMATCH"
        ok &= got == want
        print(f"  {flag}  {sig[:46]:<46} {got[:20]}…")
    print("  self-test:", "PASS" if ok else "FAIL")
