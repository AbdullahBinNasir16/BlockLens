/* ============================================================
   A minimum-threshold slider that shows its population.

   Every account is a tick on the track — ink if it clears the threshold,
   faint if it doesn't — so the reader sees how much a setting removes
   before letting go of the thumb. The kept stretch of the track is the
   one drawn in ink, because that is the part that answers the question.

   The input underneath is a native range, so keyboard and screen-reader
   behaviour come for free; only its thumb is drawn.
   ============================================================ */

const STEPS = 1000;

export interface Scale {
  /** value → 0-1 along the track */
  toPos: (v: number) => number;
  /** 0-1 along the track → value, already snapped */
  fromPos: (p: number) => number;
}

export const linear = (min: number, max: number, step = 1): Scale => ({
  toPos: (v) => (v - min) / (max - min),
  fromPos: (p) => Math.round((min + p * (max - min)) / step) * step,
});

/** Log scale with a floor that means "any". Follower counts span two
 *  orders of magnitude, so a linear track would crowd everyone but the
 *  largest accounts into its first tenth. */
export const logScale = (min: number, max: number): Scale => ({
  toPos: (v) => (v <= min ? 0 : Math.log(v / min) / Math.log(max / min)),
  fromPos: (p) => {
    if (p <= 0.004) return 0;
    const raw = min * Math.pow(max / min, p);
    const mag = Math.pow(10, Math.floor(Math.log10(raw)) - 1);
    return Math.round(raw / mag) * mag;
  },
});

export function RangeFilter({
  label,
  value,
  floor,
  scale,
  format,
  marks,
  onChange,
}: {
  label: string;
  value: number;
  /** the value that means "no threshold" */
  floor: number;
  scale: Scale;
  format: (v: number) => string;
  /** every account's value for this measure */
  marks: number[];
  onChange: (v: number) => void;
}) {
  const pos = Math.max(0, Math.min(1, scale.toPos(value)));
  const active = value !== floor;
  const kept = marks.filter((m) => !active || m >= value).length;
  const readout = active ? `≥ ${format(value)}` : 'Any';

  return (
    <div className="bl-range" data-active={active}>
      <div className="bl-range__h">
        <span className="bl-range__l">{label}</span>
        <span className="bl-range__v num">{readout}</span>
      </div>

      <div className="bl-range__rail">
        <span className="bl-range__track" aria-hidden="true" />
        <span className="bl-range__kept" style={{ left: `${pos * 100}%` }} aria-hidden="true" />
        <span className="bl-range__ticks" aria-hidden="true">
          {marks.map((m, i) => (
            <span
              key={i}
              className="bl-range__tick"
              data-in={!active || m >= value}
              style={{ left: `${Math.max(0, Math.min(1, scale.toPos(m))) * 100}%` }}
            />
          ))}
        </span>
        <input
          type="range"
          className="bl-range__input"
          min={0}
          max={STEPS}
          step={1}
          value={Math.round(pos * STEPS)}
          aria-label={label}
          aria-valuetext={readout}
          onChange={(e) => onChange(scale.fromPos(Number(e.target.value) / STEPS))}
        />
      </div>

      <span className="bl-range__n meta">
        {kept} of {marks.length}
      </span>
    </div>
  );
}
