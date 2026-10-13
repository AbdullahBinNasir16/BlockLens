"""Build the wallet graph, cluster it, and prove the clusters mean something.

    python -m scripts.graph funders          # high-degree funder review list
    python -m scripts.graph build            # edges, clusters, wallet columns
    python -m scripts.graph features         # per-token propagated features
    python -m scripts.graph validate         # co-movement lift and controls
    python -m scripts.graph cases            # reports/cluster_cases.md
    python -m scripts.graph status

Order matters: `validate` before `features` is the right way round, because
if the lift is near 1 there is no reason to compute features at all.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select, text

from blocklens.config import CONFIG
from blocklens.graph import build as gb
from blocklens.graph import cluster as gc
from blocklens.graph import features as gf
from blocklens.graph import funding as fn
from blocklens.graph import validate as gv
from blocklens.ingest.runner import run_scope
from blocklens.store import write
from blocklens.store.db import session_scope
from blocklens.store.models import GraphEdge, TokenLabel, Wallet, WalletFeature


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(2)


# --------------------------------------------------------------------------

def cmd_funders(args: argparse.Namespace) -> int:
    """The review list the brief asks for: heavy funders, and what we think
    each one is. An unlisted address funding thousands of wallets is a gap
    in our address lists, and gaps get printed rather than absorbed."""
    with session_scope() as s:
        rows = fn.high_degree_funders(s, chain=args.chain)
    print(f"{len(rows)} addresses fund >= {fn.HIGH_DEGREE_FUNDER} wallets\n")
    print(f"{'address':<44}{'wallets':>8}{'tokens':>8}{'w/tok':>9}  "
          f"{'role':<15}{'known as'}")
    for r in rows[:args.limit]:
        print(f"{r['address']:<44}{r['wallets']:>8}{r['tokens']:>8}"
              f"{str(r['wallets_per_token']):>9}  {r['role']:<15}"
              f"{r['known_as'] or ('UNLISTED - review' if r['unlisted'] else '')}")
    infra = sum(1 for r in rows if r["role"] == "infrastructure")
    disp = sum(1 for r in rows if r["role"] == "disperser")
    unlisted = sum(1 for r in rows if r["unlisted"])
    print(f"\ninfrastructure {infra}  |  disperser {disp}  |  "
          f"unlisted and needing review {unlisted}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    with run_scope(source="graph-build", scope=f"threshold={fn.HIGH_DEGREE_FUNDER}",
                   chain=args.chain) as ctx:
        s = ctx.session
        edges, report = fn.derive_edges(s, chain=args.chain)
        print("funding:", json.dumps(report, indent=1, default=str))

        buys = gb.load_buys(s, chain=args.chain)
        f_rows = gb.funding_edge_rows(edges, chain=args.chain)
        co_rows, co_report = gb.co_purchase_edges(buys)
        print(f"\nbuys {len(buys)}, co-purchase edges {len(co_rows)}, "
              f"capped tokens {co_report['tokens_capped']}")

        g = gb.build_graph(f_rows, co_rows)
        stats = gb.stats(g)
        print("graph:", json.dumps(stats))
        if not stats["in_memory_still_appropriate"]:
            print("NOTE: node count has passed 300k; in-memory NetworkX is no "
                  "longer the right call and this should be revisited.")

        layer1 = gc.funding_components(g)
        sim = gc.similarity_graph(g)
        layer2 = gc.communities(sim)
        print(f"\nlayer 1 (provable):      {layer1.n_clusters} clusters, "
              f"largest {[len(c) for c in layer1.components[:5]]}")
        print(f"layer 2 (inferred):      {layer2.n_clusters} communities, "
              f"largest {[len(c) for c in layer2.components[:5]]}")

        # Deployers, for insiderLinked. Phase 1 never captured
        # `creator_address` - discovery reads pool creation, not contract
        # creation - so it is inferred here from the token's first mint.
        #
        # The inference, stated plainly: the address that received a token's
        # first transfer out of the zero address is its initial supply
        # holder, and for a launch that is the deployer, who mints to
        # themselves and then adds liquidity. Measured on this data: all 408
        # tokens with a mint sent it to a wallet, never to a pool, which is
        # what that pattern looks like. It is an inference and not a receipt
        # - reading the creation transaction would be proof, and that needs
        # a transaction index we do not have keylessly - so `insider_reason`
        # says "initial supply holder" rather than "deployer".
        if args.infer_deployers:
            minted = s.execute(text("""
                select distinct on (token_address) token_address, to_address
                from transfer
                where chain = :chain and from_address = :zero
                order by token_address, block_number, log_index
            """), {"chain": args.chain, "zero": fn.ZERO}).all()
            token_rows = [{
                "address": token, "chain": args.chain,
                "creator_address": holder.lower(), "provenance": "live",
            } for token, holder in minted]
            if token_rows:
                res_t = write.write_tokens(s, token_rows, as_of_ts=now_utc())
                print(f"inferred {len(token_rows)} initial supply holders "
                      f"({res_t.updated} tokens updated)")
                s.commit()

        deployers = dict(s.execute(text("""
            select creator_address, address from token
            where chain = :chain and creator_address is not null
        """), {"chain": args.chain}).all())
        insider = gc.insider_links(g, layer1, deployers=deployers)
        print(f"insider-linked wallets:  {len(insider)} "
              f"(from {len(deployers)} known deployers)")

        if args.dry_run:
            print("\n--dry-run: nothing written")
            return 0

        # Edges, through the gate. `as_of_ts` is now: these are edges we
        # know about today, not edges as of a past cutoff.
        now = datetime.now(timezone.utc)
        all_rows = f_rows + [{**e, "chain": args.chain} for e in co_rows]
        res = write.write_graph_edges(s, all_rows, as_of_ts=now)
        ctx.add_rows(res.total)
        print(f"\nwrote {res.inserted} new edges, {res.updated} updated")

        # Wallet columns: funding, both cluster layers, insider reason.
        all_wallets = {r[0] for r in s.execute(text(
            "select address from wallet where chain = :chain"),
            {"chain": args.chain}).all()}
        wallet_rows = fn.wallet_rows(edges, chain=args.chain,
                                     all_wallets=all_wallets)
        # Confidence is a property of the community, so it is computed once
        # per community rather than once per member. Computing it per wallet
        # rebuilt a 5,402-node subgraph 5,402 times, and the build did not
        # finish.
        conf_by_community = {
            i: gc.confidence(sim, comp)
            for i, comp in enumerate(layer2.components, start=1)
        }
        for row in wallet_rows:
            a = row["address"]
            cid = layer2.cluster_of.get(a)
            row["cluster_id"] = layer1.cluster_of.get(a)
            row["cluster_size"] = layer1.size_of.get(a)
            row["community_id"] = cid
            row["community_confidence"] = conf_by_community.get(cid)
            row["insider_linked"] = a in insider
            row["insider_reason"] = insider.get(a)
        res_w = write.write_wallets(s, wallet_rows, as_of_ts=now)
        ctx.add_rows(res_w.total)
        print(f"updated {res_w.total} wallet rows")
        s.commit()
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """The evidence. Three numbers together, and a positive control."""
    with session_scope() as s:
        edges, _ = fn.derive_edges(s, chain=args.chain)
        buys = gb.load_buys(s, chain=args.chain)
        actions = gb.load_market_actions(s, chain=args.chain)

    f_rows = gb.funding_edge_rows(edges, chain=args.chain)
    co_rows, _ = gb.co_purchase_edges(buys)
    g = gb.build_graph(f_rows, co_rows)
    layer1 = gc.funding_components(g)
    shuffled = gc.funding_components(gv.shuffled_funding_graph(g))

    out: dict = {"generated": datetime.now(timezone.utc).isoformat(),
                 "graph": gb.stats(g),
                 "layer1_clusters": layer1.n_clusters,
                 "cluster_size_distribution": layer1.distribution(),
                 "measurements": {}}

    for name, data in (("buys_only", buys), ("buy_or_sell", actions)):
        idx = gv.BuyIndex.build(data)
        real = gv.co_movement_lift(idx, layer1.components, note=name)
        ctrl = gv.co_movement_lift(idx, shuffled.components,
                                   note=f"{name}, degree-preserving shuffle")
        summary = gv.summarise(real, ctrl)
        summary["wallets_with_activity"] = len(idx.wallets)
        out["measurements"][name] = summary
        print(f"\n--- {name}  ({len(idx.wallets)} wallets with activity)")
        print(f"  real      pairs={real.cluster_pairs:>6} "
              f"rate={real.cluster_rate:.4f}  random={real.random_rate:.4f}  "
              f"LIFT={real.lift:.2f}")
        print(f"  shuffled  pairs={ctrl.cluster_pairs:>6} "
              f"rate={ctrl.cluster_rate:.4f}  LIFT={ctrl.lift:.2f}")
        print(f"  collapse ratio: {summary['control_collapse_ratio']}")
        print(f"  verdict: {summary['verdict']}")

    # Positive control: a known funder and its known fundees, recovered.
    biggest = max(layer1.components, key=len) if layer1.components else set()
    funder = None
    for e in edges:
        if e.wallet in biggest:
            funder = e.funder
            break
    if funder:
        fundees = sorted({e.wallet for e in edges if e.funder == funder})[:40]
        synth = gv.synthetic_positive_control(funder, fundees)
        rec = gc.funding_components(synth)
        recovered = len(rec.components[0]) if rec.components else 0
        expected = len(fundees) + 1
        out["positive_control"] = {
            "funder": funder, "fundees": len(fundees),
            "recovered_in_one_component": recovered,
            "expected": expected,
            "passed": recovered == expected,
        }
        print(f"\npositive control: funder {funder[:14]} with {len(fundees)} "
              f"fundees -> recovered {recovered}/{expected} "
              f"{'PASS' if recovered == expected else 'FAIL'}")

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, default=str), encoding="utf8")
    print(f"\nwrote {path}")
    return 0


def cmd_features(args: argparse.Namespace) -> int:
    """Features per wallet per token, each frozen at that token's cutoff.

    One graph per cutoff. That is the expensive way round and it is the only
    correct one: a graph built from today's edges, used to score a launch
    from July, would hand every feature three months of hindsight.
    """
    with run_scope(source="graph-features",
                   scope=gf.FEATURE_SET_VERSION, chain=args.chain) as ctx:
        s = ctx.session
        tokens = s.execute(
            select(TokenLabel.token_address, TokenLabel.launch_ts)
            .where(TokenLabel.chain == args.chain)
            .order_by(TokenLabel.launch_ts).limit(args.limit)
        ).all()
        if not tokens:
            _die("no labelled tokens; run `python -m scripts.label build` first")

        window = CONFIG.feature_window_hours * 3600
        total_rows, total_cols = 0, 0
        for i, (token, launch) in enumerate(tokens, 1):
            as_of = datetime.fromtimestamp(launch.timestamp() + window, timezone.utc)
            edges, _ = fn.derive_edges(s, chain=args.chain, as_of_ts=as_of)
            buys = gb.load_buys(s, chain=args.chain, as_of_ts=as_of)
            co_rows, _ = gb.co_purchase_edges(buys)
            g = gb.build_graph(gb.funding_edge_rows(edges, chain=args.chain), co_rows)
            layer1 = gc.funding_components(g)
            base = gf.load_wallet_behaviour(s, chain=args.chain, as_of_ts=as_of)

            # Only the wallets that touched this token: the features exist to
            # score this launch, and a wallet that never saw it is not part
            # of that question.
            touched = {b.wallet for b in buys if b.token == token}
            vectors = {
                w: gf.features_for(g, w, base,
                                   cluster_size=layer1.size_of.get(w, 0))
                for w in touched
            }
            if not vectors:
                print(f"[{i}/{len(tokens)}] {token[:14]} no wallets touched it")
                continue
            rows = gf.rows_for_write(vectors, chain=args.chain,
                                     token_address=token, as_of_ts=as_of,
                                     computed_at=datetime.now(timezone.utc))
            res = write.write_wallet_features(s, rows, as_of_ts=as_of)
            s.commit()
            ctx.add_rows(res.total)
            total_rows += res.total
            total_cols = max(total_cols, max(r["n_features"] for r in rows))
            print(f"[{i}/{len(tokens)}] {token[:14]} {len(vectors):>5} wallets "
                  f"x {total_cols} features  (as of {as_of:%Y-%m-%d %H:%M})")

        print(f"\n{total_rows} feature rows, {total_cols} columns each")
    return 0


def cmd_cases(args: argparse.Namespace) -> int:
    """Write up the largest clusters by hand-readable evidence."""
    with session_scope() as s:
        edges, _ = fn.derive_edges(s, chain=args.chain)
        buys = gb.load_buys(s, chain=args.chain)
        f_rows = gb.funding_edge_rows(edges, chain=args.chain)
        co_rows, _ = gb.co_purchase_edges(buys)
        g = gb.build_graph(f_rows, co_rows)
        layer1 = gc.funding_components(g)
        idx = gv.BuyIndex.build(gb.load_market_actions(s, chain=args.chain))

        funder_of = {}
        for e in edges:
            funder_of.setdefault(e.wallet, e.funder)

        L = ["# Cluster cases", "",
             f"The {args.n} largest provable funding clusters, "
             f"generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. "
             "Addresses are included so every claim here can be checked on "
             "a block explorer.", "",
             "These are layer-one clusters: every member is joined to the "
             "others by a chain of actual transfers. Nothing here is "
             "inferred from behaviour.", ""]

        for rank, comp in enumerate(layer1.components[:args.n], 1):
            members = sorted(comp)
            funders = {}
            for m in members:
                f = funder_of.get(m)
                if f:
                    funders[f] = funders.get(f, 0) + 1
            top_funders = sorted(funders.items(), key=lambda kv: -kv[1])[:3]
            tokens: dict[str, int] = {}
            active = 0
            for m in members:
                acts = idx.by_wallet.get(m) or {}
                if acts:
                    active += 1
                for t in acts:
                    tokens[t] = tokens.get(t, 0) + 1
            top_tokens = sorted(tokens.items(), key=lambda kv: -kv[1])[:5]

            L += [f"## Cluster {rank}: {len(members)} wallets", "",
                  f"- **Members**: {len(members)}",
                  f"- **Wallets with any market action**: {active} "
                  f"({active / len(members):.1%})",
                  f"- **Distinct tokens touched**: {len(tokens)}",
                  ""]
            if top_funders:
                L.append("Funding pattern — the addresses that fed this cluster:")
                L.append("")
                L.append("| Funder | Wallets fed |")
                L.append("|---|---|")
                for addr, n in top_funders:
                    L.append(f"| `{addr}` | {n} |")
                L.append("")
            if top_tokens:
                L.append("| Token | Members who traded it |")
                L.append("|---|---|")
                for addr, n in top_tokens:
                    L.append(f"| `{addr}` | {n} |")
                L.append("")
            L.append("Sample members:")
            L.append("")
            for m in members[:12]:
                acts = len(idx.by_wallet.get(m) or {})
                L.append(f"- `{m}` — {acts} token(s) traded")
            if len(members) > 12:
                L.append(f"- ... and {len(members) - 12} more")
            L.append("")

            shape = ("one address fed nearly all of them, which is a "
                     "disperser pattern" if top_funders and
                     top_funders[0][1] > len(members) * 0.5 else
                     "fed from several addresses, so the component is a chain "
                     "rather than a fan-out")
            L += [f"**Reading**: {shape}. "
                  f"{active} of {len(members)} members ever traded, so the "
                  f"co-movement evidence for this cluster rests on that "
                  f"subset.", ""]

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf8")
    print(f"wrote {path} ({args.n} clusters)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    with session_scope() as s:
        def n(model, *where):
            return s.scalar(select(func.count()).select_from(model).where(*where)) or 0

        print(f"graph edges        {n(GraphEdge, GraphEdge.chain == args.chain):,}")
        for kind in ("funding", "co_purchase"):
            print(f"  {kind:<16} "
                  f"{n(GraphEdge, GraphEdge.chain == args.chain, GraphEdge.kind == kind):,}")
        print(f"wallet features    {n(WalletFeature, WalletFeature.chain == args.chain):,}")
        print(f"wallets            {n(Wallet, Wallet.chain == args.chain):,}")
        rows = s.execute(
            select(Wallet.funding_source, func.count())
            .where(Wallet.chain == args.chain)
            .group_by(Wallet.funding_source).order_by(func.count().desc())).all()
        print("\nfunding source distribution")
        total = sum(c for _, c in rows) or 1
        for src, c in rows:
            print(f"  {src:<10} {c:>7,}  {c / total:>6.1%}")
        clustered = n(Wallet, Wallet.chain == args.chain, Wallet.cluster_id.is_not(None))
        insider = n(Wallet, Wallet.chain == args.chain, Wallet.insider_linked.is_(True))
        print(f"\nin a provable cluster  {clustered:,}")
        print(f"insider-linked         {insider:,}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="graph", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--chain", default=CONFIG.chain)
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("funders", help="heavy-funder review list")
    f.add_argument("--limit", type=int, default=25)
    f.set_defaults(func=cmd_funders)

    b = sub.add_parser("build", help="edges, clusters, wallet columns")
    b.add_argument("--dry-run", action="store_true")
    b.add_argument("--no-infer-deployers", dest="infer_deployers",
                   action="store_false",
                   help="skip inferring initial supply holders from mints")
    b.set_defaults(infer_deployers=True)
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("validate", help="co-movement lift and controls")
    v.add_argument("--out", default="reports/cluster_validation.json")
    v.set_defaults(func=cmd_validate)

    ft = sub.add_parser("features", help="per-token propagated features")
    ft.add_argument("--limit", type=int, default=50)
    ft.set_defaults(func=cmd_features)

    c = sub.add_parser("cases", help="write up the largest clusters")
    c.add_argument("-n", type=int, default=5)
    c.add_argument("--out", default="reports/cluster_cases.md")
    c.set_defaults(func=cmd_cases)

    st = sub.add_parser("status", help="what is in the graph tables")
    st.set_defaults(func=cmd_status)

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
