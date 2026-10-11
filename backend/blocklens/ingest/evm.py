"""EVM primitives: keccak, event topics, and log decoding.

Event topics are computed, never pasted. Part A hardcoded three of them
from memory, and they happened to be right — but only computing them
proved it, and that is how the Uniswap V4 Initialize topic was found.
"""
from __future__ import annotations

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
_M = (1 << 64) - 1


def _rotl(x: int, n: int) -> int:
    return ((x << n) | (x >> (64 - n))) & _M


def _f(a):
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
                a[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y] & _M) & b[(x + 2) % 5][y])
        a[0][0] ^= _RC[rnd]
    return a


def keccak256(data: bytes) -> bytes:
    rate = 136
    p = bytearray(data) + b"\x01" + b"\x00" * ((-len(data) - 1) % rate)
    p[-1] ^= 0x80
    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(p), rate):
        blk = p[off:off + rate]
        for i in range(rate // 8):
            a[i % 5][i // 5] ^= int.from_bytes(blk[i * 8:(i + 1) * 8], "little")
        a = _f(a)
    out = b""
    for i in range(4):
        out += a[i % 5][i // 5].to_bytes(8, "little")
    return out[:32]


def topic(signature: str) -> str:
    return "0x" + keccak256(signature.encode()).hex()


# ---- the events Phase 1 reads -------------------------------------------
TRANSFER = topic("Transfer(address,address,uint256)")
V2_SWAP = topic("Swap(address,uint256,uint256,uint256,uint256,address)")
V2_PAIR_CREATED = topic("PairCreated(address,address,address,uint256)")
V3_SWAP = topic("Swap(address,address,int256,int256,uint160,uint128,int24)")
V3_POOL_CREATED = topic("PoolCreated(address,address,uint24,int24,address)")
V4_SWAP = topic("Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)")
V4_INITIALIZE = topic("Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)")

SWAP_TOPICS = {V2_SWAP, V3_SWAP, V4_SWAP}

# Base, verified on-chain in the Part A spike rather than taken from a list
UNISWAP_V3_FACTORY = "0x33128a8fc17869897dce68ed026d694621f6fdfd"
UNISWAP_V4_POOL_MANAGER = "0x498581ff718922c3f8e6a244956af099b2652b2b"
AERODROME_FACTORY = "0x420dd381b31aef6683db6b902084cb0ffece40da"

WETH = "0x4200000000000000000000000000000000000006"
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
DAI = "0x50c5725949a6f0c72e6c4a641f24049a917db0cb"
USDBC = "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca"
QUOTE_TOKENS = {WETH, USDC, DAI, USDBC}
STABLE_QUOTES = {USDC, DAI, USDBC}
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


# ---- decoding ------------------------------------------------------------

def addr_from_topic(t: str) -> str:
    return "0x" + t[-40:].lower()


def words(data: str) -> list[str]:
    raw = data[2:] if data.startswith("0x") else data
    return [raw[i:i + 64] for i in range(0, len(raw), 64)]


def to_uint(word: str) -> int:
    return int(word, 16) if word else 0


def to_int(word: str) -> int:
    """Two's-complement signed integer — V3 and V4 amounts are signed."""
    v = int(word, 16) if word else 0
    return v - (1 << 256) if v >= (1 << 255) else v


def looks_like_address(t: str) -> bool:
    return t.startswith("0x") and len(t) == 66 and t[2:26] == "0" * 24
