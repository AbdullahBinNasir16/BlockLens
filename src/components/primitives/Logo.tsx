/* Served from /public — no bundler import, so it is one cached request
   shared by every place the mark appears. */
const mark = '/blocklens-mark.png';

interface Props {
  size?: number;
  /** show the wordmark next to the mark */
  wordmark?: boolean;
  /** render light-on-dark */
  inverse?: boolean;
  className?: string;
}

export function Logo({ size = 22, wordmark = true, inverse = false, className }: Props) {
  return (
    <span className={`bl-logo${className ? ' ' + className : ''}`} aria-label="BlockLens">
      <img
        src={mark}
        alt=""
        width={size}
        height={size}
        decoding="async"
        style={inverse ? { filter: 'invert(1)' } : undefined}
      />
      {wordmark && (
        <span
          className="bl-logo__word"
          style={{
            fontSize: size * 0.95,
            color: inverse ? 'var(--paper)' : 'var(--ink)',
          }}
        >
          blocklens
        </span>
      )}
    </span>
  );
}
