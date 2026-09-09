import { useState } from 'react';
import { chainMeta } from '../../data/projects';

/** Token identity tile. Renders the project's own logo, falling back to a
 *  monogram if the file is missing so a row never collapses. */
export function TokenMark({
  logo,
  monogram,
  chain,
  size = 36,
  radius,
  chainBadge = false,
}: {
  logo?: string;
  monogram: string;
  chain?: string;
  size?: number;
  radius?: number;
  /** overlay the chain mark on the lower-right corner */
  chainBadge?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const r = radius ?? Math.round(size * 0.28);
  const badge = Math.max(12, Math.round(size * 0.38));

  return (
    <span className="bl-tmark" style={{ width: size, height: size }}>
      {logo && !failed ? (
        <img
          className="bl-tmark__img"
          src={logo}
          alt=""
          width={size}
          height={size}
          loading="lazy"
          decoding="async"
          style={{ borderRadius: r }}
          onError={() => setFailed(true)}
        />
      ) : (
        <span
          className="bl-tmark__fallback"
          style={{ borderRadius: r, fontSize: Math.round(size * 0.36) }}
          aria-hidden="true"
        >
          {monogram}
        </span>
      )}
      {chainBadge && chain && chainMeta[chain] && (
        <img
          className="bl-tmark__chain"
          src={chainMeta[chain].logo}
          alt=""
          width={badge}
          height={badge}
          loading="lazy"
          decoding="async"
          title={chainMeta[chain].label}
        />
      )}
    </span>
  );
}

/** Chain identity: the network's own mark plus its short name. */
export function ChainDot({ chain, size = 14 }: { chain: string; size?: number }) {
  const meta = chainMeta[chain];
  if (!meta) return <span className="bl-chaindot">{chain.toUpperCase()}</span>;
  return (
    <span className="bl-chaindot" title={meta.label}>
      <img src={meta.logo} alt="" width={size} height={size} loading="lazy" decoding="async" />
      {meta.short}
    </span>
  );
}

/** Just the mark, for tight spaces. */
export function ChainMark({ chain, size = 16 }: { chain: string; size?: number }) {
  const meta = chainMeta[chain];
  if (!meta) return null;
  return (
    <img
      className="bl-chainmark"
      src={meta.logo}
      alt={meta.label}
      width={size}
      height={size}
      loading="lazy"
      decoding="async"
      title={meta.label}
    />
  );
}
