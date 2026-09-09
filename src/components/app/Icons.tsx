/* Minimal geometric icon set. 20×20 grid, 1.3 stroke, no fills.
   Kept inline so there is no icon-font or sprite request. */

const base = {
  viewBox: '0 0 20 20',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.3,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
};

export const Icon = {
  New: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 17} height={p.size ?? 17}>
      <rect x="3" y="3" width="6" height="6" rx="1.8" />
      <rect x="11" y="3" width="6" height="6" rx="1.8" />
      <rect x="3" y="11" width="6" height="6" rx="1.8" />
      <path d="M14 11.5v5M11.5 14h5" />
    </svg>
  ),
  Trend: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 17} height={p.size ?? 17}>
      <path d="M3 13.5l4-4.5 3 3 6.5-7" />
      <path d="M12.5 5h4v4" />
    </svg>
  ),
  Launch: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 17} height={p.size ?? 17}>
      <circle cx="10" cy="10" r="6.5" />
      <path d="M10 6.5V10l2.5 1.5" />
    </svg>
  ),
  Watch: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 17} height={p.size ?? 17}>
      <path d="M5.5 3.5h9v13l-4.5-3.4L5.5 16.5z" />
    </svg>
  ),
  History: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 17} height={p.size ?? 17}>
      <circle cx="10" cy="10" r="7" />
      <path d="M10 6v4.3l2.8 1.7" />
    </svg>
  ),
  /* a funnel — the screener narrows a population rather than listing one */
  Screen: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 17} height={p.size ?? 17}>
      <path d="M3.2 4.2h13.6L11.4 10v6l-2.8-1.7V10z" />
    </svg>
  ),
  /* a pie with one slice lifted — a book, and the part of it working */
  Portfolio: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 17} height={p.size ?? 17}>
      <path d="M9 4.2a6.3 6.3 0 106.8 6.8H9z" />
      <path d="M11.4 2.6a6.4 6.4 0 016 6h-6z" />
    </svg>
  ),
  /* a person with broadcast arcs — an account whose voice carries */
  Kol: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 17} height={p.size ?? 17}>
      <circle cx="8" cy="7" r="2.8" />
      <path d="M2.8 16.2c.4-2.9 2.5-4.7 5.2-4.7s4.8 1.8 5.2 4.7" />
      <path d="M14.6 5.2a3.6 3.6 0 010 4.6M16.7 3.4a6.4 6.4 0 010 8.2" />
    </svg>
  ),
  Settings: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 17} height={p.size ?? 17}>
      <path d="M3.5 6h13M3.5 14h13" />
      <circle cx="8" cy="6" r="2.1" />
      <circle cx="13" cy="14" r="2.1" />
    </svg>
  ),
  Collapse: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 16} height={p.size ?? 16}>
      <path d="M11.5 5.5L7 10l4.5 4.5" />
      <path d="M15.5 4v12" />
    </svg>
  ),
  Expand: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 16} height={p.size ?? 16}>
      <path d="M8.5 5.5L13 10l-4.5 4.5" />
      <path d="M4.5 4v12" />
    </svg>
  ),
  Copy: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 14} height={p.size ?? 14}>
      <rect x="7" y="7" width="9" height="9" rx="2" />
      <path d="M13 7V5.5A1.5 1.5 0 0011.5 4H5.5A1.5 1.5 0 004 5.5v6A1.5 1.5 0 005.5 13H7" />
    </svg>
  ),
  Check: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 14} height={p.size ?? 14}>
      <path d="M4 10.5l4 4 8-9" />
    </svg>
  ),
  Ext: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 13} height={p.size ?? 13}>
      <path d="M8 4H5.5A1.5 1.5 0 004 5.5v9A1.5 1.5 0 005.5 16h9a1.5 1.5 0 001.5-1.5V12" />
      <path d="M11 4h5v5M16 4l-7 7" />
    </svg>
  ),
  Menu: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 18} height={p.size ?? 18}>
      <path d="M3 6h14M3 10h14M3 14h14" />
    </svg>
  ),
  Star: (p: { size?: number; filled?: boolean }) => (
    <svg
      {...base}
      width={p.size ?? 15}
      height={p.size ?? 15}
      fill={p.filled ? 'currentColor' : 'none'}
    >
      <path d="M10 3.2l2.1 4.3 4.7.7-3.4 3.3.8 4.7-4.2-2.2-4.2 2.2.8-4.7L3.2 8.2l4.7-.7z" />
    </svg>
  ),
  Arrow: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 14} height={p.size ?? 14}>
      <path d="M4 10h12M11.5 5.5L16 10l-4.5 4.5" />
    </svg>
  ),
  Search: (p: { size?: number }) => (
    <svg {...base} width={p.size ?? 15} height={p.size ?? 15}>
      <circle cx="9" cy="9" r="5" />
      <path d="M12.8 12.8L16.5 16.5" />
    </svg>
  ),
};
