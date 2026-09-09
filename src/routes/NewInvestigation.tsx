import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { datasets, chainMeta, CHAINS } from '../data/projects';
import { TokenMark, ChainMark } from '../components/primitives/TokenMark';

const SAMPLES = Object.values(datasets).map((d) => d.project);

export function NewInvestigation() {
  const nav = useNavigate();
  const [ca, setCa] = useState('');
  const [chain, setChain] = useState('base');
  const [touched, setTouched] = useState(false);

  const value = ca.trim();
  const valid = value.length === 0 ? null : value.length >= 26;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);
    const addr = value || SAMPLES[0].contract;
    if (value && !valid) return;
    nav(`/app/investigating?ca=${encodeURIComponent(addr)}&chain=${chain}`);
  };

  return (
    <div className="bl-new">
      <div className="bl-new__arc" aria-hidden="true">
        <svg viewBox="0 0 800 400" preserveAspectRatio="xMidYMax meet">
          <path d="M0,400 A400,400 0 0 1 800,400" fill="none" stroke="var(--rule)" strokeWidth="1" />
          <path
            d="M70,400 A330,330 0 0 1 730,400"
            fill="none"
            stroke="var(--rule-faint)"
            strokeWidth="1"
          />
          <path
            d="M140,400 A260,260 0 0 1 660,400"
            fill="none"
            stroke="var(--rule-faint)"
            strokeWidth="1"
          />
        </svg>
      </div>

      <div className="bl-new__inner">
        <p className="eyebrow">Workspace</p>
        <h1 className="display d2 bl-new__h">New Investigation</h1>
        <p className="lede bl-new__sub">Enter a contract address to investigate a project.</p>

        <form className="bl-new__form" onSubmit={submit}>
          <div className="bl-field">
            <label className="eyebrow" htmlFor="ca">
              Contract address
            </label>
            <input
              id="ca"
              className="bl-field__input num"
              placeholder="0x…"
              value={ca}
              spellCheck={false}
              autoComplete="off"
              autoFocus
              onChange={(e) => setCa(e.target.value)}
              data-invalid={touched && valid === false}
            />
            <span className="bl-field__note meta">
              {touched && valid === false
                ? 'That does not look like a contract address.'
                : 'Paste an address from any supported chain.'}
            </span>
          </div>

          <div className="bl-field">
            <label className="eyebrow">Select chain</label>
            <div className="bl-chainrow">
              {CHAINS.map((c) => (
                <button
                  key={c}
                  type="button"
                  className="bl-chainbtn"
                  data-on={chain === c}
                  onClick={() => setChain(c)}
                >
                  <ChainMark chain={c} size={18} />
                  <span className="bl-chainbtn__b">
                    <span className="bl-chainbtn__l">{chainMeta[c].label}</span>
                    <span className="bl-chainbtn__s meta">{chainMeta[c].short}</span>
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="bl-new__actions">
            <button className="bl-btn bl-btn--xl" type="submit">
              Investigate <span aria-hidden="true">→</span>
            </button>
          </div>

          <div className="bl-samples">
            <span className="eyebrow">Or open one already indexed</span>
            <div className="bl-samples__row">
              {SAMPLES.map((p) => (
                <button
                  key={p.id}
                  className="bl-samplechip"
                  type="button"
                  onClick={() => {
                    setCa(p.contract);
                    setChain(p.chain);
                  }}
                >
                  <TokenMark
                    logo={p.logo}
                    monogram={p.monogram}
                    chain={p.chain}
                    size={26}
                    radius={8}
                  />
                  <span className="bl-samplechip__b">
                    <span className="bl-samplechip__n">{p.name}</span>
                    <span className="meta">${p.ticker}</span>
                  </span>
                </button>
              ))}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
