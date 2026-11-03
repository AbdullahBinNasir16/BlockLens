# BlockLens: scope

What the project does and does not do, and why. The evidence behind each
decision is in `DECISIONS.md`; the FYP-1 module plan is in
`docs/FYP1_SCOPE.md`.

## Descoped: KOL scoring

**Decision (2026-10-19):** KOL scoring is out of scope. The KOL page has
been removed from the product.

**Why:**
- The only source of what promoters post is the X API.
- The X API has no free tier for reading posts. It charges per post read,
  about **$0.005** each at its published price.
- No keyless substitute exists.

The data cost was not justified against what the module would add.

**What the cost is, honestly.** It was **never measured** against a paid
call:
- No X key was bought, and no post was ever read.
- The client (`backend/blocklens/ingest/xapi.py`) is built and tested
  against a recorded fixture, and locked at a budget of 0 posts.

The figure that matters is an estimate. It multiplies a measured rate by
the published price:
- **The rate (measured):** the forward record scored about 700 Base launches
  a day (2026-10-19 to 2026-11-03).
- **The assumption:** judging whether promoters "called" a launch needs
  roughly 20 post reads per launch (a search on its ticker and address).
- **The estimate:** 700 × 20 × $0.005 ≈ **$70 a day, about $2,100 a month**.
  That is before reading any promoter's history to score them.

The rate is measured. The 20 posts per launch is an assumption, and the
price is published but not verified on our own account.

**What this removes from the original proposal:**
- The KOL directory: accounts, win rates and a "call" history per account.
- The KOL and social sections of the per-project intelligence profile
  (mentions, reach, social growth, narrative map).
- Any social signal as a model input.

**What replaces the social signal: nothing.** It is not replaced, and no
proxy for it is presented as one. The product's two signals are:
- launch type (who holds the liquidity);
- the buyer-loss model.

Both come from on-chain data alone.

**In the UI:**
- The KOL page, its navigation entry and its components were removed in
  PR #3 (2026-10-22). The code is recoverable from git history, at the
  commit before that merge.
- No KOL number appears anywhere in the product.

## Not built, and said so on screen

- **The case studies' research sections** (Nockchain, Sibyl, Dot) are
  sample.
  - Sourced figures were captured on 9 Sep 2026 and are badged as that day's
    snapshot.
  - The rest are illustrative.
  - Only the Live section (market, contract flags, the model's view) is
    live.
- **The model is scored only where it was built to be.** That means a Base
  Uniswap V3/V4 pool the live feed scored at its own launch + 5 minutes.
  Every other token shows "Outside the model's scope" and the reason.
- **Chains other than Base** are not measured or served.

## What the brief assumed that was not so (Phase 7)

| The brief said | What is true |
|---|---|
| Pydantic models were generated from `types.ts` in Phase 0 | No generator existed. Phase 7 builds one: `npm run contract` → `contract/blocklens.schema.json` → `backend/blocklens/api/contract.py`, with drift tests on both sides |
| The model outputs a calibrated probability | It does not. Forward, its scores ran about four times too high (Brier 0.038 against 0.023 for the base rate, `reports/forward_validation.md`). Scores are shown as a ranking, read through the forward record's band |
| "Of tokens like this, N in 100 ended as rugs" | The model predicts buyer loss, not rugs. Rug risk is launch type. The panel says "N in 100 lost half their value by hour 6", from the forward record |
| The Portfolio agent is not built | It is: the paper agent (Phase 9), live since 2026-10-19, beating buy-everything forward |
| The KOL page shows "Cobie at 91" | It was already removed (PR #3) |
| Trending works only under the dev server | Production also worked, through nginx and Vercel rewrites, but the browser still called the three sources itself. Phase 7 moves them behind the API |
| The screener's logic would work untouched on real positions | It did not quite. It read the sample registry and the sample clock directly. Those are now handed to it as a corpus; the logic itself is unchanged |
