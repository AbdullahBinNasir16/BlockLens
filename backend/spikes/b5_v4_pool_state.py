"""Phase 2 spike: can one V4 pool's state be read at a historical block?

This is the load-bearing unknown. B4 proved `balanceOf(quote, pair)` gives
an exact quote reserve at any block for V2, V3 and Aerodrome CL pools - but
not for Uniswap V4, where a single PoolManager holds every pool's funds at
once (4,211 WETH across all of them). V4 is ~95% of what discovery finds on
Base, so a method that excludes it excludes the dataset.

Two candidate routes, measured against a real V4 pool from our own store:

1. **StateView**, the official read-only companion to the PoolManager,
   which exposes `getSlot0(poolId)` and `getLiquidity(poolId)`. Its address
   is not taken on faith: several candidates are probed and judged by
   whether the answer is self-consistent.
2. **`extsload(bytes32)`** on the PoolManager itself, which V4 exposes for
   exactly this purpose. The pool's state lives at
   `keccak256(poolId . POOLS_SLOT)`; slot 6 is the documented mapping.

Either one, if it answers at old blocks, costs one call per sample point -
the same price as B4's balance sampling.

Throwaway. Not part of the system.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blocklens.ingest.evm import keccak256   # noqa: E402

OUT = Path(__file__).parent / "B5_v4_pool_state.json"
BLOCKS_PER_DAY = 43_200
RPC = "https://base.gateway.tenderly.co"
POOL_MANAGER = "0x498581ff718922c3f8e6a244956af099b2652b2b"

# Three live V4 pools from our own store, busiest first.
POOL_IDS = [
    "0xecd18f47c23b14d77b3a95c2c5c4be0f60a38a86c998a4a4c67292932a8a3950",
    "0xc6e38c87d7f2afabf1c342b7ee3cc113e092f79d6cf2e49de474ff3e57b0343c",
    "0x6dfced638ee679ea4b7f2d644e15d168e6a56f4872c1b22c47abe7eb31157fd8",
]

# Published StateView deployments for Base; which (if any) is right is a
# measurement, not an assumption.
STATE_VIEW_CANDIDATES = [
    "0xa3c0c9b65bad0b08107aa264b0f3db444b867a71",
    "0x7ffe42c4a5deea5b0fec41c94c136cf115597227",
    "0x571291b572ed32ce6751a2cb2486ebee8defb9b4",
]

SIG_GET_SLOT0 = "0x" + keccak256(b"getSlot0(bytes32)").hex()[:8]
SIG_GET_LIQUIDITY = "0x" + keccak256(b"getLiquidity(bytes32)").hex()[:8]
SIG_EXTSLOAD = "0x" + keccak256(b"extsload(bytes32)").hex()[:8]
POOLS_SLOT = 6

TIMEOUT = httpx.Timeout(connect=10.0, read=40.0, write=10.0, pool=10.0)


def rpc(client, method, params):
    r = client.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": method,
                               "params": params})
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(str(body["error"])[:170])
    return body["result"]


def call(client, to: str, data: str, block="latest"):
    tag = block if isinstance(block, str) else hex(block)
    return rpc(client, "eth_call", [{"to": to, "data": data}, tag])


def pool_state_slot(pool_id: str) -> str:
    """keccak256(poolId . uint256(POOLS_SLOT)) - V4's pools mapping."""
    raw = bytes.fromhex(pool_id[2:]) + POOLS_SLOT.to_bytes(32, "big")
    return "0x" + keccak256(raw).hex()


def decode_slot0(word: str) -> dict:
    """Slot0 packs sqrtPriceX96 (160) | tick (24) | protocolFee (24) | lpFee (24)."""
    v = int(word[2:66] if len(word) > 66 else word[2:], 16)
    sqrt_price = v & ((1 << 160) - 1)
    tick = (v >> 160) & ((1 << 24) - 1)
    if tick >= (1 << 23):
        tick -= (1 << 24)
    return {"sqrtPriceX96": sqrt_price, "tick": tick,
            "price_ratio": (sqrt_price / (2 ** 96)) ** 2 if sqrt_price else 0.0}


def main() -> None:
    results = {}
    with httpx.Client(timeout=TIMEOUT, headers={"user-agent": "blocklens-spike/0.1"}) as c:
        head = int(rpc(c, "eth_blockNumber", []), 16)
        results["head"] = head
        print(f"head {head:,}")
        print(f"getSlot0 selector     {SIG_GET_SLOT0}")
        print(f"getLiquidity selector {SIG_GET_LIQUIDITY}")
        print(f"extsload selector     {SIG_EXTSLOAD}\n")

        pid = POOL_IDS[0]

        print("Q1 extsload on the PoolManager (no extra deployment needed)")
        ext = {}
        slot = pool_state_slot(pid)
        print(f"  state slot for pool {pid[:14]}... = {slot[:18]}...")
        for label, blk in (("latest", "latest"), ("-7d", head - 7 * BLOCKS_PER_DAY),
                           ("-30d", head - 30 * BLOCKS_PER_DAY),
                           ("-90d", head - 90 * BLOCKS_PER_DAY)):
            try:
                word = call(c, POOL_MANAGER, SIG_EXTSLOAD + slot[2:], blk)
                dec = decode_slot0(word)
                ext[label] = {"ok": True, "raw": word[:66], **dec}
                print(f"  {label:<7} OK   tick={dec['tick']:>8}  "
                      f"sqrtP={dec['sqrtPriceX96']:>28}")
            except Exception as e:  # noqa: BLE001
                ext[label] = {"ok": False, "error": str(e)[:150]}
                print(f"  {label:<7} FAIL {str(e)[:95]}")
            time.sleep(0.2)
        results["extsload"] = ext

        print("\nQ2 StateView candidates (judged by whether they agree with extsload)")
        sv = {}
        for addr in STATE_VIEW_CANDIDATES:
            row = {}
            try:
                w = call(c, addr, SIG_GET_SLOT0 + pid[2:], "latest")
                row["slot0_raw"] = w[:200]
                row["words"] = (len(w) - 2) // 64
                # getSlot0 returns (sqrtPriceX96, tick, protocolFee, lpFee)
                if row["words"] >= 2:
                    row["sqrtPriceX96"] = int(w[2:66], 16)
                    t = int(w[66:130], 16)
                    row["tick"] = t - (1 << 256) if t >= (1 << 255) else t
                row["ok"] = True
                print(f"  {addr}  OK  words={row['words']} "
                      f"tick={row.get('tick')} sqrtP={row.get('sqrtPriceX96')}")
            except Exception as e:  # noqa: BLE001
                row = {"ok": False, "error": str(e)[:130]}
                print(f"  {addr}  FAIL {str(e)[:70]}")
            sv[addr] = row
            time.sleep(0.2)
        results["stateview"] = sv

        print("\nQ3 does extsload agree across all three of our pools")
        agree = {}
        for p in POOL_IDS:
            try:
                word = call(c, POOL_MANAGER, SIG_EXTSLOAD + pool_state_slot(p)[2:], "latest")
                d = decode_slot0(word)
                agree[p[:14]] = d
                print(f"  {p[:14]}...  tick={d['tick']:>8}  "
                      f"ratio={d['price_ratio']:.3e}")
            except Exception as e:  # noqa: BLE001
                agree[p[:14]] = {"error": str(e)[:120]}
                print(f"  {p[:14]}...  FAIL {str(e)[:80]}")
            time.sleep(0.2)
        results["all_pools"] = agree

        print("\nQ4 liquidity for a pool, which is what a 'reserve' means on V4")
        # In V4 the pool's liquidity sits one word past slot0 in the struct.
        liq = {}
        base = int(pool_state_slot(pid), 16)
        for label, blk in (("latest", "latest"), ("-90d", head - 90 * BLOCKS_PER_DAY)):
            try:
                word = call(c, POOL_MANAGER,
                            SIG_EXTSLOAD + f"{base + 3:064x}", blk)
                liq[label] = int(word[2:66], 16)
                print(f"  liquidity {label:<7} {liq[label]:,}")
            except Exception as e:  # noqa: BLE001
                liq[label] = {"error": str(e)[:120]}
                print(f"  liquidity {label:<7} FAIL {str(e)[:80]}")
            time.sleep(0.2)
        results["liquidity_slot_plus3"] = liq

    OUT.write_text(json.dumps(results, indent=1, default=str), encoding="utf8")
    print(f"\nwrote {OUT.name}")


if __name__ == "__main__":
    main()
