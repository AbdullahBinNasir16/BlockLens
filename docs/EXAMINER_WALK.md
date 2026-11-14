# Walking BlockLens as an examiner (Phase 7, 2026-11-03)

I walked the production build, as an examiner trying to catch it out.
- **Setup:** `vite build` pointed at the API on another origin, so no proxy
  could help it; then `vite preview`.
- **Every screen twice:** once with the API up, and once with every API
  request blocked in the browser.
- **The odd paths too:** a random contract address, a non-address, a
  Solana address, an unknown case-study id, and the screener end to end
  with the wallet drawer.

Automated and kept as tests in `e2e/fallback.spec.ts` and
`e2e/smoke.spec.ts`; 13 pass against the build.

## What was wrong, and is now fixed

| # | What an examiner would have seen | Fix |
|---|---|---|
| 1 | The landing page's footer strip: "BASE · BLOCK 24,182,904 · TX/S 41.2 · PROJECTS TRACKED 12,480". These were invented constants shown as live readings. Base was at about block 53.4M | Read live from `/api/health` (the block scanned to, launches in the last 6h, the model version), or "live feed offline". No number otherwise |
| 2 | The landing page's chain picker offered Ethereum, Solana and BNB Chain | Shown disabled: "not supported" |
| 3 | The case study's "24h" price sparkline was generated from a seed | Removed |
| 4 | The case study's "Overall Risk" rings (Overview, Final Assessment) had no badge. "Where does 72 come from?" had no answer on screen | An amber Sample badge, plus "an illustrative case-study score… not the BlockLens model" |
| 5 | The raw model output was shown as a probability ("75% · chance a minute-5 buy is worth ≤ half at hour 6"). It is not calibrated: forward, scores ran about four times too high | The model's view is "about 49 in 100": the forward rate in that score's band. The raw score is shown as 0.75, "a ranking, not a probability". It is never a percentage anywhere |
| 6 | The case studies' "Sourced" sections, captured on 9 Sep, carried a green badge | Amber: "snapshot of 9 Sep 2026, not live" |
| 7 | With the API down, the Trending page's Sample badge was cut off the screen. A CSS class (`.bl-live`) was defined twice, and the live pages' header was 6px wide | The landing dot is renamed `.bl-livedot` |
| 8 | The live screener returned 0 wallets for every search: its search window was computed from a clock of zero (1970) | The corpus clock comes from the token index |
| 9 | The screener showed "Average hold 4.7 months" for positions observed for only 24 hours | Positions carry `observedUntil`; open positions are measured only to it |
| 10 | Screener filters with no data behind them (funding source, cluster size, smart money, labels, honeypots, wallet age, first seen) would silently match nothing | Shown disabled and struck through on the live corpus, with the reason |
| 11 | A GoPlus outage showed "—" under a green Live badge with no reason; "Holders 0" for a token GoPlus has not indexed | The reason is stated; 0 reads "not yet indexed by GoPlus" |
| 12 | Empty states (nothing shown at all) carried a "Sample data" chip | A neutral "No data" chip |
| 13 | Nockchain's model panel said the feed "saw it launching" in October. It saw a new pool for an old token | "The live feed saw a pool for this token open on…" |

## What is still wrong, or I could not defend

1. **Third-party numbers are shown verbatim.** A 45-minute-old token
   (UTDF) showed a **$197.65M market cap and $29.65M liquidity** on 151
   trades. That is DexScreener's figure; liquidity like that is easy to
   fake. Nothing sanity-checks it. "Is that real?" can only be answered
   with "it is what DexScreener reports".
2. **A new pool for an old token can be scored.** The feed watches pools,
   not tokens. 20 such pools were seen and none was scored, but no guard
   stops one. Its score would be out of distribution.
3. **The landing page's coverage list promises more than exists.** It lists
   Developers, GitHub, Fundamentals and History as dimensions of an
   investigation. Those exist only for the three case studies, and are
   sample.
4. **The live screener shows address stubs, not names** ("5f28…"). The
   research store holds no symbols for most of its 771 launches.
5. **A fresh install is thin.**
   - The screener needs the research store, so on a clean machine it shows
     its sample corpus, badged.
   - Every token is "outside the model's scope" until the feed scores new
     launches.
   - The forward record and paper agent start empty.

   `RUNNING.md` says so, but on screen it looks bare.
6. **The clean-machine Docker path was not run on this machine,** which
   cannot run Docker. It is exercised by CI's "Clean machine · docker
   compose up" job on a fresh runner, which runs on the pull request.
7. **The snapshots age.** The sample fallbacks (Trending, Fresh Launches,
   Model Health, Paper Agent) are frozen on 3 Nov 2026, and the banner
   names the date.
   - The Paper Agent snapshot holds only the latest 400 trades, so its
     policy figures differ from the full record.
   - Its badge says "latest 400 trades".
8. **The Watchlist and History have no sample.** With the API down they
   say "API unreachable". This is deliberate: a sample of someone's own
   records would be fake personal data. But it is the one screen type that
   does not degrade to sample.
9. **GoPlus throttles after about 10 lookups.** Trending's holder column
   fills slowly, and the first viewers see "—".
10. **The KOL code was deleted (PR #3), not kept** as the brief preferred.
    It is recoverable from git history.
11. **The X cost is an estimate, not a measurement:** a measured launch
    rate × an assumed 20 posts per launch × the published price.
    `SCOPE.md` says which part is which.
