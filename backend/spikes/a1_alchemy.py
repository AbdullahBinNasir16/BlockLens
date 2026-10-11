"""A1/A2, the part that needs a key: does the free plan serve
alchemy_getAssetTransfers at full block range, and what does it cost?

Run with a free key:

    ALCHEMY_API_KEY=xxxx python a1_alchemy.py

It answers four things, in order:

1. Does a single call over the widest possible range (block 0 -> latest) get
   rejected on the free plan? That is the question Part A was written to
   settle and the only one that cannot be inferred.
2. For each token already measured by log scan, how many pages and transfers
   does a complete first 24 hours take?
3. Does the transfer count agree with the independent log-scan ground truth in
   measurements.json? A mismatch means getAssetTransfers is not complete for
   our purposes, and would matter more than the cost.
4. What is the eth_getLogs cap on this key, probed directly rather than taken
   from the docs.

Compute units are NOT returned in the response. Alchemy only exposes them in
the dashboard, so this script reports calls and pages, and multiplies by the
published price to estimate CU. Read the real figure off the dashboard before
and after a run and record the difference in FINDINGS.md.
"""
import json
import os
import sys
import time

from _http import STATS, rpc, save

KEY = os.environ.get("ALCHEMY_API_KEY", "").strip()
if not KEY:
    sys.exit("ALCHEMY_API_KEY is not set. Get a free key at alchemy.com and re-run:\n"
             "  ALCHEMY_API_KEY=xxxx python a1_alchemy.py")

URL = f"https://base-mainnet.g.alchemy.com/v2/{KEY}"
PAGE = 1_000
# published prices, to be confirmed against the dashboard
CU_TRANSFERS = 120
CU_GETLOGS = 60
CU_TX = 26
MONTHLY_CU = 30_000_000


def widest_range_test():
    """The headline question: full history in one call, accepted or refused?"""
    print("1. widest possible range, single call (block 0 -> latest)")
    t0 = time.time()
    res, err = rpc(URL, "alchemy_getAssetTransfers",
                   [{"fromBlock": "0x0", "toBlock": "latest",
                     "category": ["erc20"], "maxCount": hex(PAGE),
                     "contractAddresses": ["0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"]}],
                   allow_error=True, retries=1, timeout=90)
    dt = round(time.time() - t0, 1)
    if err:
        print(f"   REFUSED after {dt}s: {str(err)[:200]}")
        return {"accepted": False, "error": str(err)[:300], "seconds": dt}
    n = len(res.get("transfers", []))
    print(f"   ACCEPTED in {dt}s: {n} transfers, pageKey {'present' if res.get('pageKey') else 'absent'}")
    return {"accepted": True, "transfers_first_page": n,
            "has_page_key": bool(res.get("pageKey")), "seconds": dt}


def token_day(tok):
    """Every transfer in the token's first 24 hours, paginated to exhaustion."""
    start, end = tok["start_block"], tok["end_block"]
    page_key, pages, transfers, t0 = None, 0, 0, time.time()
    while True:
        params = {"fromBlock": hex(start), "toBlock": hex(end),
                  "category": ["erc20", "external"], "maxCount": hex(PAGE),
                  "contractAddresses": [tok["token"]]}
        if page_key:
            params["pageKey"] = page_key
        res, err = rpc(URL, "alchemy_getAssetTransfers", [params],
                       allow_error=True, retries=2, timeout=90)
        pages += 1
        if err:
            return {"symbol": tok["symbol"], "error": str(err)[:300], "pages": pages}
        transfers += len(res.get("transfers", []))
        page_key = res.get("pageKey")
        if not page_key:
            break
        if pages > 200:            # a runaway would burn the month's allowance
            return {"symbol": tok["symbol"], "error": "stopped at 200 pages", "pages": pages}
        time.sleep(0.1)

    measured = tok["transfers_24h"]
    return {
        "symbol": tok["symbol"], "token": tok["token"],
        "blocks": [start, end], "pages": pages, "transfers": transfers,
        "seconds": round(time.time() - t0, 1),
        "log_scan_ground_truth": measured,
        # external transfers are included here and absent from the log scan,
        # so Alchemy returning more is expected; fewer would be a problem
        "at_least_as_complete": transfers >= measured,
        "cu_estimated": pages * CU_TRANSFERS,
    }


def getlogs_cap():
    """The documented 10-block cap, probed on this key."""
    print("\n4. eth_getLogs range cap on this key")
    head, _ = rpc(URL, "eth_blockNumber", [], retries=3)
    h = int(head, 16)
    best = 0
    for span in (1, 10, 100, 1_000, 10_000):
        to_b = h - 50_000
        _, err = rpc(URL, "eth_getLogs",
                     [{"fromBlock": hex(to_b - span + 1), "toBlock": hex(to_b),
                       "address": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"}],
                     allow_error=True, retries=1, timeout=45)
        print(f"   {span:>6} blocks: {'ok' if not err else 'refused — ' + str(err)[:90]}")
        if err:
            break
        best = span
        time.sleep(0.3)
    return {"max_range": best,
            "calls_per_token_day": (43_200 // best + 1) if best else None,
            "cu_per_token_day": (43_200 // best + 1) * CU_GETLOGS if best else None}


def main():
    print("Alchemy spike — free plan, Base\n")
    out = {"widest_range": widest_range_test()}

    print("\n2/3. per-token first 24 hours, against the log-scan ground truth")
    try:
        measured = json.load(open("measurements.json", encoding="utf8"))
        retry = json.load(open("measurements_retry.json", encoding="utf8"))
        by = {m["symbol"]: m for m in measured}
        by.update({m["symbol"]: m for m in retry})
        toks = list(by.values())
    except FileNotFoundError:
        sys.exit("measurements.json is missing — run a2_measure.py first")

    rows = []
    for tok in toks:
        r = token_day(tok)
        rows.append(r)
        if "error" in r:
            print(f"   {r['symbol']:<8} FAILED after {r['pages']} pages: {r['error'][:90]}")
        else:
            flag = "ok" if r["at_least_as_complete"] else "INCOMPLETE vs log scan"
            print(f"   {r['symbol']:<8} {r['pages']:>3} pages  {r['transfers']:>6} transfers "
                  f"(log scan saw {r['log_scan_ground_truth']}) {flag}  "
                  f"~{r['cu_estimated']} CU  {r['seconds']}s")
    out["tokens"] = rows
    out["getlogs"] = getlogs_cap()

    good = [r for r in rows if "error" not in r]
    if good:
        cu = [r["cu_estimated"] for r in good]
        worst, mean = max(cu), sum(cu) / len(cu)
        out["summary"] = {
            "cu_per_token_min": min(cu), "cu_per_token_mean": round(mean), "cu_per_token_max": worst,
            "tokens_per_month_at_worst": MONTHLY_CU // worst,
            "tokens_per_month_at_mean": int(MONTHLY_CU / mean),
            "tokens_per_month_with_wallet_attribution":
                MONTHLY_CU // max(r["cu_estimated"] + CU_TX * t["transfer_txs_24h"]
                                  for r, t in zip(good, toks) if "error" not in r),
        }
        print(f"\n   CU/token: min {min(cu)} mean {round(mean)} max {worst}")
        print(f"   tokens/month: {MONTHLY_CU // worst:,} at worst, "
              f"{int(MONTHLY_CU / mean):,} at mean")
    save("a1_alchemy.json", out)
    save("http_stats_alchemy.json", STATS.report())
    print("\n   Now read actual CU off the Alchemy dashboard and put the real number in FINDINGS.md.")


if __name__ == "__main__":
    main()
