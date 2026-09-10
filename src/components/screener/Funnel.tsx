import type { FunnelStage } from '../../data/types';
import { int } from '../../lib/format';

/* The funnel is the search's audit trail, reduced to one line: what each
   stage kept, and what it took away. A small result set is explained
   rather than merely delivered. */

export function Funnel({ stages }: { stages: FunnelStage[] }) {
  return (
    <ol className="bl-funnel" aria-label="How the wallets were narrowed">
      {stages.map((s) => (
        <li key={s.id} className="bl-funnel__s" data-empty={s.remaining === 0 && s.removed > 0}>
          <span className="bl-funnel__n num">{int(s.remaining)}</span>
          <span className="bl-funnel__l">{s.label}</span>
          {s.removed > 0 && <span className="bl-funnel__d num">−{int(s.removed)}</span>}
        </li>
      ))}
    </ol>
  );
}
