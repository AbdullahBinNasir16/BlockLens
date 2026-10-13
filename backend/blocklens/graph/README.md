# The wallet graph

This module collapses many addresses back into one actor, and proves the
collapse corresponds to something before anything is built on it.

**Read this first, because it bounds every claim below:** this is not an
ETH-funding trace. The brief specified one, built from
`alchemy_getAssetTransfers` with each wallet as `toAddress`. That method is
affordable — 14,097 wallets at 120 CU a page is 1.69M CU, 5.6% of a free
month, well inside the 20% ceiling the brief set — but there is no Alchemy
key in this environment and Part A established that one cannot be created
here, so the allowance to spend against is zero. No keyless substitute
exists for the question "every inbound transfer to this address, ever":
native ETH funding leaves no log to filter, and `eth_getLogs` is capped at
1,000 blocks however narrowly the query is written (measured, spike B1).

So the edges here are **token-acquisition provenance**, derived from the
56,296 wallet-to-wallet transfers Phase 1 already stored. That is a real
relationship and it catches the pattern this module exists for — one address
fed 5,400 wallets across 5 tokens in this dataset — but it is a weaker claim
than ETH ancestry, and the differences matter:

* a wallet that only ever bought from a pool is **`unknown`**, not `fresh`.
  How it got its gas is exactly what we cannot see.
* two wallets funded from the same exchange hot wallet are invisible as a
  pair — and would have been anyway, since an exchange's internal ledger is
  not on chain.

## Data flow

```
transfer (Phase 1)
    |
    |  funding.derive_edges          first non-infrastructure sender per wallet
    |      - address lists           known_addresses/*.json
    |      - degree profiling        infrastructure vs disperser
    v
funding edges  ----------------+
                               |
transfer (Phase 1)             |
    |                          |
    |  build.load_buys         |     token leaving a pool to a wallet
    v                          |
buys                           |
    |  build.co_purchase_edges |     same token, within 300 s
    v                          v
co-purchase edges -------> build.build_graph  (NetworkX, in memory)
                               |
            +------------------+------------------+
            v                                     v
   cluster.funding_components            cluster.similarity_graph
   LAYER 1: provable                             |
   wallet.cluster_id                             v
                                        cluster.communities
                                        LAYER 2: inferred
                                        wallet.community_id + confidence
            |
            v
   features.load_wallet_behaviour  ->  features.features_for
                                        95 features per wallet per token,
                                        base + 1-hop + 2-hop aggregates
            |
            v
   write.write_wallet_features  (through the Phase 1 gate, with as_of_ts)
            |
            v
   validate.co_movement_lift  +  shuffled control  +  positive control
```

## The two layers, and why they never merge

| | Layer 1 | Layer 2 |
|---|---|---|
| method | connected components over funding edges | greedy modularity over a weighted similarity graph |
| claim | these wallets are **joined by actual transfers** | these wallets **behave like** one actor |
| columns | `cluster_id`, `cluster_size` | `community_id`, `community_confidence` |
| precision | high | lower, and scored |

Kept in separate columns because "which of these can you prove and which did
you infer" has to have an answer in the schema. Collapsing them into one
number would destroy the only distinction that matters when someone asks.

Layer 2 uses **Louvain with a fixed seed**. Greedy modularity was chosen
first, because it is deterministic without needing a seed at all - a
stronger guarantee. It did not survive the real graph: CNM failed to
complete on ~15,000 nodes and ~96,000 edges in over ten minutes, and an
algorithm that does not finish offers no determinism. Louvain is seeded
explicitly and `test_graph.py` asserts three consecutive runs agree.

## Infrastructure versus dispersers

A router must never create an edge — a wallet "funded by" the Uniswap router
is an artefact of how a swap settles. The curated lists in
`known_addresses/` make the common cases legible and are **incomplete by
construction**; what actually protects the graph is degree.

But degree alone is the wrong test, and getting this wrong emptied the graph
once. Measured on this data:

| Address | Wallets | Tokens | Wallets/token | Role |
|---|---|---|---|---|
| Uniswap V4 PoolManager | 3,366 | 219 | 15 | infrastructure |
| LI.FI / Jumper | 143 | 16 | 9 | infrastructure |
| `0xd152f549…` | 5,400 | **5** | 1,080 | disperser |
| `0xe9132055…` | 942 | **1** | 942 | disperser |

Infrastructure serves the whole chain, so it touches many tokens. An address
touching thousands of wallets across a handful of tokens is distributing
something specific, which is the sybil pattern. Excluding on wallet count
alone built **451 edges from 14,507 wallets**; splitting on token spread
built **14,525**.

Whether a disperser's fundees are a farm or a genuine airdrop is *not*
decided by this rule. It is decided by whether they co-move, which is what
`validate.py` measures.

## Known limits

- **A centralised exchange breaks the trace completely.** Two wallets funded
  from the same hot wallet are not evidence of one actor, because the
  exchange's ledger is off chain. We cannot follow it and we do not claim to.
- **The CEX list is empty.** Attributing a Base address to a named exchange
  needs a labelled source, and every one is paid or blocked here (Basescan
  paid, Blockscout 403). Rather than present guesses as curated data the
  list is unpopulated, so `cex` is 0% in every distribution and wallets a
  real exchange funded land elsewhere — overstating `cluster` and `fresh`.
  The high-degree review list is the mitigation, and it is reported.
- **The bridge list covers only the OP Stack predeploys.** Third-party
  bridges are not enumerated, so a wallet funded through one is not
  classified as `bridge`.
- **Hop limit is 2.** Each hop multiplies the neighbourhood and dilutes the
  signal; at three hops, on a graph containing 5,000-wallet dispersers,
  nearly every wallet reaches nearly every other and the feature stops
  distinguishing anything. Peel chains longer than two hops are not followed
  and their actors are not grouped.
- **Deployers are inferred, not read.** `creator_address` comes from the
  recipient of a token's first mint, which for a launch is the deployer
  minting to themselves. Reading the creation transaction would be proof and
  needs a transaction index we do not have keylessly, so `insider_reason`
  says "initial supply holder".
- **Co-purchase is a coincidence until it is aggregated.** Thousands of
  people buy the same launch in the same minute. A single shared buy is
  worth almost nothing and only ever feeds the probabilistic layer.

## Ethics, by construction rather than by policy

**We group pseudonymous addresses. We do not attempt to identify people, and
nothing in this module tries to.**

That is structural, not a promise. There is no code here that joins to a
name, a handle, an IP, an exchange KYC record or any off-chain identity, and
no field in `wallet`, `graph_edge` or `wallet_feature` can hold one. The
curated lists name *contracts* — routers, bridges, pools — never persons.
`insider_linked` relates an address to another address and stores the
on-chain reason it was related.

The strongest claim this module can make about a wallet is that it moved
tokens in a pattern shared with other wallets. That is deliberately all.
