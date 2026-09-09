import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { verdictColor, verdictMark } from '../../lib/format';

/* ---------------- Tag / pill ---------------- */

export function Tag({
  children,
  tone = 'neutral',
  solid = false,
  size = 'md',
}: {
  children: React.ReactNode;
  tone?: 'neutral' | 'positive' | 'negative' | 'warn' | 'ink';
  solid?: boolean;
  size?: 'sm' | 'md';
}) {
  return (
    <span className="bl-tag" data-tone={tone} data-solid={solid} data-size={size}>
      {children}
    </span>
  );
}

/* ---------------- Provenance chip ---------------- */

/** Presentational half of the provenance marker. Research sections read the
 *  flag from project context; surfaces outside a project — the screener —
 *  pass it directly. Both render the same chip so the convention holds. */
export function ProvChip({ live, note }: { live: boolean; note?: string }) {
  return (
    <span
      className="bl-prov"
      data-live={live}
      title={
        note ??
        (live
          ? 'Figures in this section come from public sources.'
          : 'Illustrative data. Shapes are representative; the numbers are not findings.')
      }
    >
      <span className="bl-prov__dot" />
      {live ? 'Sourced' : 'Sample'}
    </span>
  );
}

/* ---------------- Verdict mark ---------------- */

export function VerdictMark({ status, label }: { status: string; label?: string }) {
  return (
    <span className="bl-verdict" style={{ color: verdictColor[status] }}>
      <span className="bl-verdict__m">{verdictMark[status]}</span>
      {label && <span className="bl-verdict__l">{label}</span>}
    </span>
  );
}

/* ---------------- Section header ---------------- */

export function SectionHead({
  index,
  title,
  sub,
  right,
  id,
}: {
  index: string;
  title: string;
  sub?: string;
  right?: React.ReactNode;
  id?: string;
}) {
  return (
    <header className="bl-sechead" id={id}>
      <div className="bl-sechead__mark">
        <svg viewBox="0 0 40 40" width="34" height="34" aria-hidden="true">
          <circle cx="20" cy="20" r="18" fill="none" stroke="var(--ink)" strokeWidth="1" />
          <text
            x="20"
            y="20"
            textAnchor="middle"
            dominantBaseline="central"
            fontFamily="var(--mono)"
            fontSize="12"
            fill="var(--ink)"
            letterSpacing="0.04em"
          >
            {index}
          </text>
        </svg>
      </div>
      <div className="bl-sechead__body">
        <h2 className="bl-sechead__t display d3">{title}</h2>
        {sub && <p className="bl-sechead__s">{sub}</p>}
      </div>
      {right && <div className="bl-sechead__r">{right}</div>}
    </header>
  );
}

/* ---------------- Stat ---------------- */

export function Stat({
  label,
  value,
  sub,
  tone,
  align = 'left',
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  tone?: string;
  align?: 'left' | 'right';
}) {
  return (
    <div className="bl-stat" style={{ textAlign: align }}>
      <span className="bl-stat__l eyebrow">{label}</span>
      <span className="bl-stat__v num" style={tone ? { color: tone } : undefined}>
        {value}
      </span>
      {sub && <span className="bl-stat__s meta">{sub}</span>}
    </div>
  );
}

/* ---------------- Side drawer ---------------- */

export function Drawer({
  open,
  onClose,
  title,
  eyebrow,
  children,
  width = 460,
}: {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  eyebrow?: string;
  children: React.ReactNode;
  width?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    ref.current?.focus();
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  /* Portalled to <body> because a drawer opened from inside a sticky or
     transformed ancestor is trapped in that ancestor's stacking context —
     its z-index stops meaning anything, and later content paints over it.
     The screener's query rail is sticky, which is how this surfaced. */
  return createPortal(
    <div className="bl-drawer" role="dialog" aria-modal="true">
      <button className="bl-drawer__scrim" onClick={onClose} aria-label="Close panel" />
      <aside className="bl-drawer__panel" style={{ width }} ref={ref} tabIndex={-1}>
        <header className="bl-drawer__head">
          <div>
            {eyebrow && <span className="eyebrow">{eyebrow}</span>}
            <div className="bl-drawer__title">{title}</div>
          </div>
          <button className="bl-drawer__x" onClick={onClose} aria-label="Close">
            <svg viewBox="0 0 20 20" width="18" height="18">
              <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.4" fill="none" />
            </svg>
          </button>
        </header>
        <div className="bl-drawer__body">{children}</div>
      </aside>
    </div>,
    document.body
  );
}

/* ---------------- Empty state ---------------- */

export function EmptyNote({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="bl-empty">
      <svg viewBox="0 0 48 48" width="34" height="34" aria-hidden="true">
        <circle cx="24" cy="24" r="22" fill="none" stroke="var(--rule-strong)" strokeWidth="1" strokeDasharray="3 4" />
        <line x1="16" y1="24" x2="32" y2="24" stroke="var(--ink-4)" strokeWidth="1.2" />
      </svg>
      <div>
        <p className="bl-empty__t">{title}</p>
        {detail && <p className="bl-empty__d meta">{detail}</p>}
      </div>
    </div>
  );
}

/* ---------------- Key/value row ---------------- */

export function KV({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) {
  return (
    <div className="bl-kv">
      <span className="bl-kv__k meta">{k}</span>
      <span className="bl-kv__v num" style={tone ? { color: tone } : undefined}>
        {v}
      </span>
    </div>
  );
}
