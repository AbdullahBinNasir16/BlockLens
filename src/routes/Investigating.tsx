import { useEffect, useRef, useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { shortAddr } from '../lib/format';
import { chainMeta, findByContract } from '../data/projects';
import { TokenMark, ChainMark } from '../components/primitives/TokenMark';
import { recordInvestigation } from '../lib/live/product';

type Step = { group: string; label: string; ms: number };

const STEPS: Step[] = [
  { group: 'Identifying project', label: 'Contract found', ms: 340 },
  { group: 'Identifying project', label: 'Token metadata resolved', ms: 260 },
  { group: 'Identifying project', label: 'Pair and deployer located', ms: 300 },

  { group: 'Collecting on-chain data', label: 'Holders discovered', ms: 380 },
  { group: 'Collecting on-chain data', label: 'Liquidity identified', ms: 280 },
  { group: 'Collecting on-chain data', label: 'Transfer history indexed', ms: 340 },

  { group: 'Investigating project', label: 'Website found', ms: 260 },
  { group: 'Investigating project', label: 'X account found', ms: 240 },
  { group: 'Investigating project', label: 'Repository matched', ms: 320 },

  { group: 'Analyzing people', label: 'Developer history', ms: 400 },
  { group: 'Analyzing people', label: 'KOL performance record', ms: 380 },
  { group: 'Analyzing people', label: 'Wallet clustering', ms: 340 },

  { group: 'Connecting evidence', label: 'Historical relationships', ms: 360 },
  { group: 'Connecting evidence', label: 'Claims tested against evidence', ms: 320 },
  { group: 'Connecting evidence', label: 'Final intelligence', ms: 300 },
];

const GROUPS = STEPS.reduce<string[]>((acc, s) => {
  if (!acc.includes(s.group)) acc.push(s.group);
  return acc;
}, []);

export function Investigating() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const ca = params.get('ca') ?? '';
  const chain = params.get('chain') ?? 'base';

  const [i, setI] = useState(0);
  const timer = useRef<number>();

  /* Only a project we have researched gets the research flow. Anything else
     goes straight to the honest empty state: playing "claims tested against
     evidence" and then showing a sample profile under a real token's name
     would present fabricated findings as research. */
  const match = findByContract(ca);
  const target = match?.project.id;
  const resolved = match?.project;

  const logged = useRef(false);
  useEffect(() => {
    if (!target || logged.current) return;
    logged.current = true;
    recordInvestigation(ca, 'profile');
  }, [target, ca]);

  useEffect(() => {
    if (!target) return;
    if (i >= STEPS.length) {
      timer.current = window.setTimeout(
        () => nav(`/app/project/${target}`, { replace: true }),
        620
      );
      return () => window.clearTimeout(timer.current);
    }
    timer.current = window.setTimeout(() => setI((n) => n + 1), STEPS[i].ms);
    return () => window.clearTimeout(timer.current);
  }, [i, nav, target]);

  const done = Math.min(i, STEPS.length);
  const pctRaw = (done / STEPS.length) * 100;
  const pct = Math.round(pctRaw);
  const currentGroup = STEPS[Math.min(i, STEPS.length - 1)].group;

  const R = 62;
  const C = 2 * Math.PI * R;

  if (!target) {
    return <Navigate to={`/app/token/${encodeURIComponent(ca)}?chain=${chain}`} replace />;
  }

  return (
    <div className="bl-inv">
      <div className="bl-inv__head">
        <div className="bl-inv__ident">
          {resolved && i > 2 && (
            <TokenMark
              logo={resolved.logo}
              monogram={resolved.monogram}
              chain={resolved.chain}
              size={44}
              radius={14}
            />
          )}
          <div>
            <p className="eyebrow">
              {resolved && i > 2 ? `Investigating ${resolved.name}` : 'Investigating'}
            </p>
            <p className="bl-inv__addr num">{shortAddr(ca, 14, 8)}</p>
          </div>
        </div>
        <span className="bl-tag" data-tone="ink">
          <ChainMark chain={chain} size={13} />
          {chainMeta[chain]?.label ?? chain}
        </span>
      </div>

      <div className="bl-inv__body">
        {/* ---------------- checklist ---------------- */}
        <ol className="bl-inv__list">
          {GROUPS.map((g) => {
            const items = STEPS.map((s, idx) => ({ ...s, idx })).filter((s) => s.group === g);
            const first = items[0].idx;
            const last = items[items.length - 1].idx;
            const state = i > last ? 'done' : i >= first ? 'active' : 'pending';

            return (
              <li key={g} className="bl-invgroup" data-state={state}>
                <p className="bl-invgroup__t">{g}</p>
                <ul className="bl-invgroup__items">
                  {items.map((s) => {
                    const st = i > s.idx ? 'done' : i === s.idx ? 'active' : 'pending';
                    return (
                      <li key={s.label} className="bl-invitem" data-state={st}>
                        <span className="bl-invitem__m" aria-hidden="true">
                          {st === 'done' ? '✓' : st === 'active' ? '●' : '○'}
                        </span>
                        <span className="bl-invitem__l">{s.label}</span>
                      </li>
                    );
                  })}
                </ul>
              </li>
            );
          })}
        </ol>

        {/* ---------------- indicator ---------------- */}
        <div className="bl-inv__meter">
          <div className="bl-inv__ring">
            <svg viewBox="0 0 160 160" width="180" height="180" aria-hidden="true">
              <circle cx="80" cy="80" r={R} fill="none" stroke="var(--rule)" strokeWidth="3" />
              <circle
                cx="80"
                cy="80"
                r={R}
                fill="none"
                stroke="var(--ink)"
                strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray={C}
                strokeDashoffset={C * (1 - pctRaw / 100)}
                transform="rotate(-90 80 80)"
                style={{ transition: 'stroke-dashoffset 320ms var(--ease)' }}
              />
              {STEPS.map((_, idx) => {
                const a = (idx / STEPS.length) * 360;
                return (
                  <line
                    key={idx}
                    x1="80"
                    y1="8"
                    x2="80"
                    y2="13"
                    stroke={idx < done ? 'var(--ink)' : 'var(--rule-strong)'}
                    strokeWidth="1.2"
                    transform={`rotate(${a} 80 80)`}
                  />
                );
              })}
            </svg>
            <span className="bl-inv__pct num">{pct}</span>
          </div>
          <p className="bl-inv__stage">{i >= STEPS.length ? 'Compiling profile' : currentGroup}</p>
          <p className="meta bl-inv__count">
            {done} / {STEPS.length} checks
          </p>
          <div className="bl-inv__sweep" aria-hidden="true">
            <span />
          </div>
        </div>
      </div>
    </div>
  );
}
