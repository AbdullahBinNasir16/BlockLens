import { useState } from 'react';
import type { AppliedCheck, Chain, CheckDefinition, CheckTier, Project, Quantifier, ScreenerQuery } from '../../data/types';
import { CATEGORY_LABEL, CATEGORY_ORDER, CHECKS, QUANTIFIER_LABEL } from '../../data/checks';
import { CHAINS, chainMeta, datasets, findByContract } from '../../data/projects';
import { PRESETS, WINDOW_PRESETS, makeCheck, windowRange } from '../../data/presets';
import { dateInput, dateShort, shortAddr } from '../../lib/format';
import { TokenMark } from '../primitives/TokenMark';
import { DerivedRing, FilterChip } from './FilterChip';

/* ============================================================
   The screener's question, in the order a person asks it: which chain,
   which contracts, over what period, and what a wallet has to have done.
   Everything combines with AND — there is no OR and no nesting, so
   nothing here suggests one.
   ============================================================ */

/* ---------------- contract resolution ---------------- */

const EVM = /^0x[0-9a-fA-F]{40}$/;
const SOL = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

const validFor = (chain: Chain, ca: string) => (chain === 'solana' ? SOL : EVM).test(ca);

export type ContractStatus =
  | { kind: 'ok'; project: Project }
  | { kind: 'wrongChain'; project: Project }
  | { kind: 'unknown' };

/** What the product knows about a pasted address on the chosen chain. A
 *  backend would answer this from its token index when the address is
 *  added; here the registry stands in. */
export function resolveContract(ca: string, chain: Chain): ContractStatus {
  const hit = findByContract(ca);
  if (!hit) return { kind: 'unknown' };
  return hit.project.chain === chain
    ? { kind: 'ok', project: hit.project }
    : { kind: 'wrongChain', project: hit.project };
}

export const searchableCount = (q: ScreenerQuery) =>
  q.scope.contracts.filter((c) => resolveContract(c, q.scope.chain).kind === 'ok').length;

/* ---------------- window ---------------- */

function activeWindow(from: number, to: number): string {
  for (const w of WINDOW_PRESETS) {
    const r = windowRange(w.id);
    if (r.from === from && r.to === to) return w.id;
  }
  return 'custom';
}

/* ---------------- step rows ---------------- */

function Step({ n, label, children }: { n: string; label: string; children: React.ReactNode }) {
  return (
    <div className="bl-step">
      <div className="bl-step__h">
        <span className="bl-step__n num">{n}</span>
        <span className="bl-step__l">{label}</span>
      </div>
      <div className="bl-step__b">{children}</div>
    </div>
  );
}

function ContractsField({
  query,
  onChange,
}: {
  query: ScreenerQuery;
  onChange: (q: ScreenerQuery) => void;
}) {
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { chain, contracts } = query.scope;
  const chainName = chainMeta[chain].label;

  const add = (raw: string) => {
    const ca = raw.trim();
    if (!ca) return;
    if (!validFor(chain, ca)) {
      setError(`That isn’t a valid ${chainName} address.`);
      return;
    }
    if (contracts.some((c) => c.toLowerCase() === ca.toLowerCase())) {
      setError('Already added.');
      return;
    }
    onChange({ ...query, scope: { ...query.scope, contracts: [...contracts, ca] } });
    setText('');
    setError(null);
  };

  const remove = (ca: string) =>
    onChange({ ...query, scope: { ...query.scope, contracts: contracts.filter((c) => c !== ca) } });

  /* the prototype's index, offered as addresses rather than names — the
     product takes contracts, and a demo still needs something to paste */
  const indexed = Object.values(datasets)
    .map((d) => d.project)
    .filter((p) => p.chain === chain)
    .filter((p) => !contracts.some((c) => c.toLowerCase() === p.contract.toLowerCase()));

  return (
    <div className="bl-cas">
      <form
        className="bl-cas__form"
        data-error={!!error}
        onSubmit={(e) => {
          e.preventDefault();
          add(text);
        }}
      >
        <input
          className="bl-cas__input num"
          value={text}
          placeholder={`Paste a ${chainName} contract address`}
          spellCheck={false}
          autoComplete="off"
          aria-label="Contract address"
          onChange={(e) => {
            setText(e.target.value);
            if (error) setError(null);
          }}
        />
        <button type="submit" className="bl-cas__add" aria-label="Add contract" title="Add contract">
          <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
            <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="1.8" fill="none" />
          </svg>
        </button>
      </form>
      {error && <p className="bl-cas__err meta">{error}</p>}

      {contracts.length > 0 && (
        <ul className="bl-cas__list">
          {contracts.map((ca) => {
            const s = resolveContract(ca, chain);
            return (
              <li key={ca} className="bl-ca" data-kind={s.kind}>
                {s.kind === 'unknown' ? (
                  <span className="bl-ca__blank" aria-hidden="true" />
                ) : (
                  <TokenMark logo={s.project.logo} monogram={s.project.monogram} size={22} radius={7} />
                )}
                <span className="bl-ca__b">
                  {s.kind !== 'unknown' && <span className="bl-ca__t">{s.project.ticker}</span>}
                  <span className="bl-ca__a num" title={ca}>
                    {shortAddr(ca, 6, 4)}
                  </span>
                </span>
                {s.kind === 'wrongChain' && (
                  <span className="bl-ca__flag meta">on {chainMeta[s.project.chain].label}</span>
                )}
                {s.kind === 'unknown' && <span className="bl-ca__flag meta">not indexed</span>}
                <button className="bl-ca__x" onClick={() => remove(ca)} aria-label={`Remove ${ca}`}>
                  <svg viewBox="0 0 20 20" width="10" height="10" aria-hidden="true">
                    <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="2" fill="none" />
                  </svg>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <p className="bl-cas__idx meta">
        {indexed.length ? (
          <>
            <span>Indexed on {chainName}</span>
            {indexed.map((p) => (
              <button key={p.id} className="bl-cas__sug num" onClick={() => add(p.contract)}>
                {shortAddr(p.contract, 6, 4)}
              </button>
            ))}
          </>
        ) : contracts.length ? null : (
          <span>No {chainName} contracts are indexed in this prototype.</span>
        )}
      </p>
    </div>
  );
}

/* ---------------- filters ---------------- */

function ChipRows({
  tier,
  query,
  onToggle,
  onChange,
}: {
  tier: CheckTier;
  query: ScreenerQuery;
  onToggle: (def: CheckDefinition) => void;
  onChange: (c: AppliedCheck) => void;
}) {
  const applied = tier === 'project' ? query.projectRule.checks : query.walletChecks;
  return (
    <div className="bl-fcats">
      {CATEGORY_ORDER.map((cat) => {
        const defs = CHECKS.filter((c) => c.tier === tier && c.category === cat);
        if (!defs.length) return null;
        return (
          <div className="bl-fcat" key={cat}>
            <span className="bl-fcat__l">{CATEGORY_LABEL[cat]}</span>
            <div className="bl-fcat__chips">
              {defs.map((def) => (
                <FilterChip
                  key={def.id}
                  def={def}
                  applied={applied.find((a) => a.checkId === def.id)}
                  onToggle={() => onToggle(def)}
                  onChange={onChange}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RuleControl({
  query,
  onChange,
  max,
}: {
  query: ScreenerQuery;
  onChange: (q: ScreenerQuery) => void;
  max: number;
}) {
  const rule = query.projectRule;
  const live = rule.checks.length > 0;
  const setRule = (patch: Partial<ScreenerQuery['projectRule']>) =>
    onChange({ ...query, projectRule: { ...rule, ...patch } });
  const ceiling = Math.max(1, max);

  return (
    <div className="bl-rule" data-live={live} aria-disabled={!live}>
      <span className="bl-rule__t">must pass in</span>
      <span className="bl-seg bl-seg--sm" role="radiogroup" aria-label="Quantifier">
        {(['atLeast', 'exactly', 'atMost'] as Quantifier[]).map((q) => (
          <button
            key={q}
            role="radio"
            aria-checked={rule.quantifier === q}
            className="bl-seg__b"
            data-on={rule.quantifier === q}
            disabled={!live}
            onClick={() => setRule({ quantifier: q })}
          >
            {QUANTIFIER_LABEL[q]}
          </button>
        ))}
      </span>
      <span className="bl-stepper">
        <button
          className="bl-stepper__b"
          disabled={!live || rule.count <= 0}
          onClick={() => setRule({ count: rule.count - 1 })}
          aria-label="Fewer projects"
        >
          −
        </button>
        <span className="bl-stepper__v num" data-over={rule.count > max}>
          {rule.count}
        </span>
        <button
          className="bl-stepper__b"
          disabled={!live || rule.count >= ceiling}
          onClick={() => setRule({ count: rule.count + 1 })}
          aria-label="More projects"
        >
          +
        </button>
      </span>
      <span className="bl-rule__t">
        of {max} {max === 1 ? 'project' : 'projects'}
      </span>
    </div>
  );
}

/* ---------------- panel ---------------- */

export function FilterPanel({
  query,
  onChange,
  onSearch,
  searching,
}: {
  query: ScreenerQuery;
  onChange: (q: ScreenerQuery) => void;
  onSearch: () => void;
  searching: boolean;
}) {
  const { scope } = query;
  const win = activeWindow(scope.from, scope.to);
  const [custom, setCustom] = useState(win === 'custom');
  const setScope = (patch: Partial<ScreenerQuery['scope']>) =>
    onChange({ ...query, scope: { ...scope, ...patch } });

  const ready = searchableCount(query);
  const filtersOn = query.projectRule.checks.length + query.walletChecks.length;

  const toggle = (def: CheckDefinition) => {
    if (def.tier === 'project') {
      const on = query.projectRule.checks.some((c) => c.checkId === def.id);
      onChange({
        ...query,
        projectRule: {
          ...query.projectRule,
          checks: on
            ? query.projectRule.checks.filter((c) => c.checkId !== def.id)
            : [...query.projectRule.checks, makeCheck(def.id)],
        },
      });
    } else {
      const on = query.walletChecks.some((c) => c.checkId === def.id);
      onChange({
        ...query,
        walletChecks: on
          ? query.walletChecks.filter((c) => c.checkId !== def.id)
          : [...query.walletChecks, makeCheck(def.id)],
      });
    }
  };

  const change = (next: AppliedCheck) => {
    const tier = CHECKS.find((c) => c.id === next.checkId)?.tier;
    if (tier === 'project') {
      onChange({
        ...query,
        projectRule: {
          ...query.projectRule,
          checks: query.projectRule.checks.map((c) => (c.checkId === next.checkId ? next : c)),
        },
      });
    } else {
      onChange({
        ...query,
        walletChecks: query.walletChecks.map((c) => (c.checkId === next.checkId ? next : c)),
      });
    }
  };

  return (
    <section className="bl-panel" aria-label="Search wallets">
      <Step n="01" label="Chain">
        <div className="bl-seg" role="radiogroup" aria-label="Chain">
          {CHAINS.map((c) => (
            <button
              key={c}
              role="radio"
              aria-checked={scope.chain === c}
              className="bl-seg__b bl-seg__b--chain"
              data-on={scope.chain === c}
              onClick={() => setScope({ chain: c })}
            >
              <img src={chainMeta[c].logo} alt="" width={16} height={16} loading="lazy" />
              {chainMeta[c].label}
            </button>
          ))}
        </div>
      </Step>

      <Step n="02" label="Contracts">
        <ContractsField query={query} onChange={onChange} />
      </Step>

      <Step n="03" label="Window">
        <div className="bl-winrow">
          <div className="bl-seg" role="radiogroup" aria-label="Window">
            {WINDOW_PRESETS.map((w) => (
              <button
                key={w.id}
                role="radio"
                aria-checked={win === w.id && !custom}
                className="bl-seg__b"
                data-on={win === w.id && !custom}
                onClick={() => {
                  setScope(windowRange(w.id));
                  setCustom(false);
                }}
              >
                {w.label}
              </button>
            ))}
            <button
              role="radio"
              aria-checked={custom || win === 'custom'}
              className="bl-seg__b"
              data-on={custom || win === 'custom'}
              onClick={() => setCustom(true)}
            >
              Custom
            </button>
          </div>
          {custom || win === 'custom' ? (
            <span className="bl-dates">
              <input
                type="date"
                className="bl-date num"
                value={dateInput(scope.from)}
                aria-label="From"
                onChange={(e) => {
                  const ms = Date.parse(`${e.target.value}T00:00:00Z`);
                  if (!Number.isNaN(ms)) setScope({ from: ms });
                }}
              />
              <span className="meta">to</span>
              <input
                type="date"
                className="bl-date num"
                value={dateInput(scope.to)}
                aria-label="To"
                onChange={(e) => {
                  const ms = Date.parse(`${e.target.value}T23:59:59Z`);
                  if (!Number.isNaN(ms)) setScope({ to: ms });
                }}
              />
            </span>
          ) : (
            <span className="meta bl-winrow__r">
              {dateShort(scope.from)} — {dateShort(scope.to)}
            </span>
          )}
        </div>
      </Step>

      <Step n="04" label="Filters">
        <div className="bl-fhead">
          <span className="meta">
            {filtersOn ? `${filtersOn} on` : 'Click a filter to switch it on'}
          </span>
          <span className="bl-fhead__r">
            <span className="meta">Presets</span>
            {PRESETS.map((p) => (
              <button key={p.id} className="bl-textbtn" onClick={() => onChange(p.apply(query))}>
                {p.label}
              </button>
            ))}
            {filtersOn > 0 && (
              <button
                className="bl-textbtn bl-textbtn--quiet"
                onClick={() =>
                  onChange({
                    ...query,
                    projectRule: { quantifier: 'atLeast', count: 1, checks: [] },
                    walletChecks: [],
                  })
                }
              >
                Clear
              </button>
            )}
          </span>
        </div>

        <div className="bl-fblock">
          <div className="bl-fblock__h">
            <span className="bl-fblock__t">In each project</span>
            <RuleControl query={query} onChange={onChange} max={ready} />
          </div>
          <ChipRows tier="project" query={query} onToggle={toggle} onChange={change} />
        </div>

        <div className="bl-fblock">
          <div className="bl-fblock__h">
            <span className="bl-fblock__t">Whole wallet</span>
            <span className="meta">measured once, across every project in scope</span>
          </div>
          <ChipRows tier="wallet" query={query} onToggle={toggle} onChange={change} />
        </div>

        <p className="bl-legend meta">
          <DerivedRing /> needs clustering, labelling or price history — sample values in this
          build
        </p>
      </Step>

      <div className="bl-searchbar">
        <span className="bl-searchbar__sum meta">
          <span>{chainMeta[scope.chain].label}</span>
          <span>
            {ready} {ready === 1 ? 'contract' : 'contracts'}
          </span>
          <span>{win === 'custom' ? 'Custom window' : WINDOW_PRESETS.find((w) => w.id === win)?.label}</span>
          <span>
            {filtersOn} {filtersOn === 1 ? 'filter' : 'filters'}
          </span>
        </span>
        <button
          className="bl-search"
          onClick={onSearch}
          disabled={ready === 0 || searching}
          title={ready === 0 ? `Add a ${chainMeta[scope.chain].label} contract to search` : undefined}
        >
          {searching ? 'Searching…' : 'Search wallets'}
          <svg viewBox="0 0 20 20" width="15" height="15" aria-hidden="true">
            <path d="M4 10h12M11.5 5.5L16 10l-4.5 4.5" stroke="currentColor" strokeWidth="1.6" fill="none" />
          </svg>
        </button>
      </div>
    </section>
  );
}
