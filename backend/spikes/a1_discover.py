"""A1, step five: find real Base tokens launched ~4 months ago.

DexScreener's search surfaces established tokens, not fresh launches, so
discovery happens on-chain: scan DEX factory events over one historical
day and take the tokens that were paired that day. Tenderly's public
gateway allows 1,000-block windows, so a day costs 44 calls.
"""
import json, time
from datetime import datetime, timezone
from _http import STATS, get_json, rpc, save

URL = "https://base.gateway.tenderly.co"
SPAN = 1_000
FACTORIES = {
    "aerodrome": "0x420dd381b31aef6683db6b902084cb0ffece40da",
    "pancakeswap": "0x02a84c1b3bbd7401a5f7fa98a384ebc70bb5749e",
    "baseswap": "0xfda619b6d20975be80a10332cd39b9a4b0faa8bb",
    "alien-base": "0x0fd83557b2be93617c9c1c1b6fd549401c74558c",
}
QUOTES = {  # the side that is not the new token
    "0x4200000000000000000000000000000000000006",  # WETH
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",  # USDC
    "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",  # DAI
    "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca",  # USDbC
}
TARGET = datetime(2026, 6, 15, tzinfo=timezone.utc)


def block_at(ts):
    """Binary search a block by timestamp."""
    head, _ = rpc(URL, "eth_blockNumber", [], retries=3)
    hi = int(head, 16)
    lo = max(1, hi - 20_000_000)
    while lo < hi:
        mid = (lo + hi) // 2
        b, err = rpc(URL, "eth_getBlockByNumber", [hex(mid), False], allow_error=True, retries=2)
        if err or not b:
            time.sleep(0.5)
            continue
        if int(b["timestamp"], 16) < ts:
            lo = mid + 1
        else:
            hi = mid
        time.sleep(0.08)
    return lo


def scan(addr, start, end, label):
    """Every log from one contract over a block range, 1,000 at a time."""
    logs, calls = [], 0
    b = start
    while b <= end:
        to_b = min(b + SPAN - 1, end)
        res, err = rpc(URL, "eth_getLogs",
                       [{"fromBlock": hex(b), "toBlock": hex(to_b), "address": addr}],
                       allow_error=True, retries=2, timeout=60)
        calls += 1
        if err:
            print(f"    ! {label} {b}-{to_b}: {str(err)[:90]}")
        else:
            logs.extend(res)
        b = to_b + 1
        time.sleep(0.12)
    return logs, calls


def main():
    start_blk = block_at(int(TARGET.timestamp()))
    print(f"  {TARGET.date()} starts at block {start_blk}")
    end_blk = start_blk + 43_200          # one Base day
    found, calls_total = {}, 0

    for dex, fac in FACTORIES.items():
        logs, calls = scan(fac, start_blk, end_blk, dex)
        calls_total += calls
        topics = {}
        for l in logs:
            topics[l["topics"][0][:10]] = topics.get(l["topics"][0][:10], 0) + 1
        print(f"  {dex:<12} {len(logs):>5} factory logs in {calls} calls  topic0s: {topics}")
        for l in logs:
            if len(l["topics"]) < 3:
                continue
            t0 = "0x" + l["topics"][1][-40:]
            t1 = "0x" + l["topics"][2][-40:]
            new = [t for t in (t0, t1) if t.lower() not in QUOTES]
            if len(new) == 1:                      # exactly one novel side
                found[new[0].lower()] = {
                    "token": new[0], "dex": dex,
                    "created_block": int(l["blockNumber"], 16),
                }
    print(f"  {len(found)} candidate tokens from {calls_total} calls")
    save("discovered.json", {"target_day": str(TARGET.date()), "start_block": start_blk,
                             "end_block": end_blk, "calls": calls_total,
                             "tokens": list(found.values())})
    save("http_stats_discover.json", STATS.report())


if __name__ == "__main__":
    main()
