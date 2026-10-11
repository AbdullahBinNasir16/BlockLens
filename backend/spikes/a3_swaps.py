"""A3: do we need swap logs, or can buys and sells be rebuilt from transfers?

Takes a real pool, finds a real Swap event, and checks what the same
transaction's Transfer logs alone would tell us: direction, both amounts,
and therefore price in the quote asset.
"""
import json, time
from _http import rpc, save

URL = "https://base.gateway.tenderly.co"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
V3_SWAP = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
V2_SWAP = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"


def s256(hexstr):
    v = int(hexstr, 16)
    return v - (1 << 256) if v >= (1 << 255) else v


def main():
    m = json.load(open("measurements.json", encoding="utf8"))
    tok = max(m, key=lambda r: r["pool_logs_24h"])
    print(f"  pool under test: {tok['symbol']} {tok['pair']}")
    print(f"  topic histogram over its first 24h:")
    for t, n in sorted(tok["pool_topic_histogram"].items(), key=lambda kv: -kv[1]):
        label = "Swap(v3)" if t == V3_SWAP else "Swap(v2)" if t == V2_SWAP else ""
        print(f"    {t[:18]}… {n:>6}  {label}")

    # find one swap, then read the whole transaction
    start = tok["start_block"]
    swap = None
    b = start
    while b < start + 43_200 and not swap:
        res, err = rpc(URL, "eth_getLogs", [{"fromBlock": hex(b), "toBlock": hex(b + 999),
                                             "address": tok["pair"]}], allow_error=True, retries=2)
        if not err:
            for l in res:
                if l["topics"][0] in (V3_SWAP, V2_SWAP):
                    swap = l
                    break
        b += 1000
        time.sleep(0.1)
    if not swap:
        print("  no swap event found"); return

    tx = swap["transactionHash"]
    rec, err = rpc(URL, "eth_getTransactionReceipt", [tx], retries=3)
    logs = rec["logs"]
    transfers = [l for l in logs if l["topics"][0] == TRANSFER and len(l["topics"]) == 3]
    pair = tok["pair"].lower()
    token = tok["token"].lower()

    print(f"\n  swap tx {tx[:18]}…  logs in tx: {len(logs)}, ERC-20 transfers: {len(transfers)}")
    recon = {"token_in": 0, "token_out": 0, "quote_in": 0, "quote_out": 0, "wallet": None}
    for l in transfers:
        src = ("0x" + l["topics"][1][-40:]).lower()
        dst = ("0x" + l["topics"][2][-40:]).lower()
        val = int(l["data"], 16)
        asset = l["address"].lower()
        side = "token" if asset == token else "quote"
        if dst == pair:
            recon[f"{side}_in"] += val
            if side == "token": recon["wallet"] = src
        elif src == pair:
            recon[f"{side}_out"] += val
            if side == "token": recon["wallet"] = dst
        print(f"    {('TOKEN' if side=='token' else 'quote'):<5} {src[:10]}… -> {dst[:10]}… {val}")

    if swap["topics"][0] == V3_SWAP:
        raw = swap["data"][2:]
        a0 = s256(raw[0:64]); a1 = s256(raw[64:128])
        print(f"\n  Swap event says: amount0={a0}  amount1={a1}")
    direction = "BUY (token left the pool)" if recon["token_out"] else "SELL (token entered the pool)"
    print(f"  Transfers alone say: {direction}, wallet {str(recon['wallet'])[:12]}…, "
          f"token {recon['token_out'] or recon['token_in']}, quote {recon['quote_in'] or recon['quote_out']}")
    save("a3_swap_reconstruction.json",
         {"token": tok["symbol"], "pair": tok["pair"], "tx": tx,
          "logs_in_tx": len(logs), "erc20_transfers_in_tx": len(transfers),
          "reconstruction": {k: str(v) for k, v in recon.items()},
          "swap_topic": swap["topics"][0],
          "pool_topic_histogram": tok["pool_topic_histogram"]})


if __name__ == "__main__":
    main()
