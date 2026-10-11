"""A1/A2/A3: the measurement that matters.

For each token, scan its complete first 24 hours on Base and count what a
backfill would actually have to carry: ERC-20 transfers, pool events, and
the wallets that bought in the first hour. One scan serves all three
questions, because the same window answers them.

Cost is reported in calls and seconds. Alchemy CU is *computed* from its
published per-method cost, not measured — there is no key in this
environment, and that is stated in the findings.
"""
import json, time
from datetime import datetime, timezone
from _http import STATS, rpc, save

URL = "https://base.gateway.tenderly.co"
SPAN = 1_000
DAY_BLOCKS = 43_200
HOUR_BLOCKS = 1_800
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO = "0x0000000000000000000000000000000000000000"


def block_at(ts):
    head, _ = rpc(URL, "eth_blockNumber", [], retries=3)
    hi = int(head, 16); lo = max(1, hi - 20_000_000)
    while lo < hi:
        mid = (lo + hi) // 2
        b, err = rpc(URL, "eth_getBlockByNumber", [hex(mid), False], allow_error=True, retries=2)
        if err or not b:
            time.sleep(0.4); continue
        if int(b["timestamp"], 16) < ts: lo = mid + 1
        else: hi = mid
        time.sleep(0.07)
    return lo


def measure(tok):
    t0 = time.time()
    start = tok.get("launch_block") or block_at(tok["created_ms"] // 1000)
    end = start + DAY_BLOCKS
    addrs = [tok["token"].lower(), tok["pair"].lower()]

    logs, calls, failed = [], 0, 0
    b = start
    while b <= end:
        to_b = min(b + SPAN - 1, end)
        res, err = rpc(URL, "eth_getLogs",
                       [{"fromBlock": hex(b), "toBlock": hex(to_b), "address": addrs}],
                       allow_error=True, retries=2, timeout=60)
        calls += 1
        if err:
            failed += 1
        else:
            logs.extend(res)
        b = to_b + 1
        time.sleep(0.1)

    token_l = tok["token"].lower()
    pair_l = tok["pair"].lower()
    transfers = [l for l in logs if l["address"].lower() == token_l and l["topics"][0] == TRANSFER]
    pool_logs = [l for l in logs if l["address"].lower() == pair_l]
    pool_topics = {}
    for l in pool_logs:
        pool_topics[l["topics"][0]] = pool_topics.get(l["topics"][0], 0) + 1

    # buyers in hour one: tokens leaving the pool to a wallet
    hour_end = start + HOUR_BLOCKS
    buyers, first_hour_transfers = set(), 0
    for l in transfers:
        if int(l["blockNumber"], 16) > hour_end:
            continue
        first_hour_transfers += 1
        src = "0x" + l["topics"][1][-40:]
        dst = "0x" + l["topics"][2][-40:]
        if src.lower() == pair_l and dst.lower() not in (pair_l, ZERO):
            buyers.add(dst.lower())

    mints = sum(1 for l in transfers if ("0x" + l["topics"][1][-40:]) == ZERO)
    txs = {l["transactionHash"] for l in transfers}
    payload = sum(len(json.dumps(l)) for l in logs)

    return {
        **{k: tok[k] for k in ("symbol", "token", "pair", "dex", "launch_day", "liq", "vol24h") if k in tok},
        "start_block": start, "end_block": end,
        "rpc_calls": calls, "failed_calls": failed,
        "seconds": round(time.time() - t0, 1),
        "transfers_24h": len(transfers),
        "transfer_txs_24h": len(txs),
        "mint_events": mints,
        "pool_logs_24h": len(pool_logs),
        "pool_topic_histogram": pool_topics,
        "first_hour_transfers": first_hour_transfers,
        "distinct_buyers_first_hour": len(buyers),
        "raw_log_bytes": payload,
    }


def main():
    picks = json.load(open("picks.json", encoding="utf8"))
    out = []
    for tok in picks:
        print(f"  measuring {tok['symbol']} ({tok['token'][:10]}) ...", flush=True)
        r = measure(tok)
        out.append(r)
        print(f"    {r['transfers_24h']} transfers / {r['transfer_txs_24h']} txs, "
              f"{r['pool_logs_24h']} pool logs, {r['distinct_buyers_first_hour']} buyers in hour 1, "
              f"{r['rpc_calls']} calls, {r['seconds']}s")
        save("measurements.json", out)
    save("http_stats_measure.json", STATS.report())


if __name__ == "__main__":
    main()
