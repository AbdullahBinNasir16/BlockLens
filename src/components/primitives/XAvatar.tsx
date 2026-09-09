import { useState } from 'react';

/* ============================================================
   X profile picture.

   Avatars are captured once into /public/avatars/<handle>.jpg so the page
   makes no third-party request at view time. If a handle has no file yet,
   a deterministic identicon stands in — the layout never collapses and the
   placeholder is obviously a placeholder.
   ============================================================ */

const SHADES = ['#2e2e2c', '#4a4a45', '#1a7f4b', '#2c5aa0', '#a8790e', '#6b6a64'];

export function XAvatar({
  handle,
  size = 40,
  ring = true,
}: {
  handle: string;
  size?: number;
  /** hairline around the image, for light avatars on paper */
  ring?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const clean = handle.replace(/^@/, '');

  if (!failed) {
    return (
      <img
        className="bl-xav"
        data-ring={ring}
        src={`/avatars/${clean}.jpg`}
        alt=""
        width={size}
        height={size}
        style={{ width: size, height: size }}
        loading="lazy"
        decoding="async"
        onError={() => setFailed(true)}
      />
    );
  }

  /* mirrored 5×5 identicon from a stable hash of the handle */
  let h = 2166136261;
  for (let i = 0; i < clean.length; i++) {
    h ^= clean.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  const ink = SHADES[h % SHADES.length];
  const on = (col: number, row: number) => (((h >> ((col * 5 + row) % 30)) ^ (h >>> 11)) & 1) === 1;

  return (
    <span
      className="bl-xav bl-xav--gen"
      data-ring={ring}
      style={{ width: size, height: size }}
      title={`@${clean} — generated placeholder`}
      aria-hidden="true"
    >
      <svg viewBox="0 0 25 25" width={size} height={size}>
        <rect width="25" height="25" fill="var(--paper-sunken)" />
        <g fill={ink}>
          {[0, 1, 2, 3, 4].map((c) =>
            [0, 1, 2, 3, 4].map((r) =>
              on(c > 2 ? 4 - c : c, r) ? (
                <rect key={`${c}-${r}`} x={c * 5} y={r * 5} width="5" height="5" />
              ) : null
            )
          )}
        </g>
      </svg>
    </span>
  );
}
