import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BlockchainPlate } from '../components/landing/BlockchainPlate';
import { MoonRug } from '../components/landing/MoonRug';
import { FlowSection } from '../components/landing/FlowSection';
import { Logo } from '../components/primitives/Logo';
import { useScrollProgress, useInView } from '../lib/hooks';
import { datasets, chainMeta, CHAINS } from '../data/projects';
import { ChainMark } from '../components/primitives/TokenMark';

/* The one case study offered from the landing page. */
const DEMO_CONTRACT = datasets.nockchain.project.contract;

const DIMENSIONS = [
  { k: 'On-chain', d: 'Holders, flow, launch mechanics' },
  { k: 'Developers', d: 'Prior deployments and outcomes' },
  { k: 'Launch type', d: 'Who holds the liquidity, read at minute 0' },
  { k: 'Buyer-loss risk', d: 'A validated model, scored once at minute 5' },
  { k: 'GitHub', d: 'Commit history and consistency' },
  { k: 'Forward record', d: 'Every prediction logged before its outcome' },
  { k: 'Fundamentals', d: 'Idea, uniqueness, innovation' },
  { k: 'History', d: 'What this team shipped before' },
  { k: 'Risk', d: 'Signals, evidence, contradiction' },
];

export function Landing() {
  const nav = useNavigate();
  const [heroRef, p] = useScrollProgress<HTMLElement>();
  const [ca, setCa] = useState('');
  const [chain, setChain] = useState('base');
  const [introRef, introSeen] = useInView<HTMLElement>();

  const go = (e?: React.FormEvent) => {
    e?.preventDefault();
    const addr = ca.trim();
    if (!addr) {
      nav('/app/new');
      return;
    }
    nav(`/app/investigating?ca=${encodeURIComponent(addr)}&chain=${chain}`);
  };

  return (
    <div className="bl-landing">
      {/* ================= nav ================= */}
      <nav className="bl-nav">
        <Link to="/" className="bl-nav__logo">
          <Logo size={21} />
        </Link>
        <div className="bl-nav__right">
          <a className="bl-nav__link" href="#process">
            Process
          </a>
          <a className="bl-nav__link" href="#coverage">
            Coverage
          </a>
          <Link className="bl-btn bl-btn--sm" to="/app/new">
            Open Workspace <span aria-hidden="true">→</span>
          </Link>
        </div>
      </nav>

      {/* ================= hero plate ================= */}
      {/* once the hero has fully scrolled past, its animations stop */}
      <header className="bl-hero" ref={heroRef} data-off={p >= 0.99}>
        <div className="bl-hero__plate">
          <BlockchainPlate p={p} />
        </div>

        <div className="bl-hero__content">
          <p className="eyebrow bl-hero__eyebrow">
            <span className="bl-live" aria-hidden="true" />
            Blockchain project intelligence
          </p>

          <h1 className="display d1 bl-hero__h">
            What is actually
            <br />
            behind this
            <br />
            contract?
          </h1>

          <form className="bl-inputrow" onSubmit={go}>
            <div className="bl-inputrow__field">
              <label className="eyebrow" htmlFor="hero-ca">
                Contract address
              </label>
              <input
                id="hero-ca"
                className="bl-input num"
                placeholder="0x…"
                value={ca}
                spellCheck={false}
                autoComplete="off"
                onChange={(e) => setCa(e.target.value)}
              />
            </div>
            <div className="bl-inputrow__chains">
              {CHAINS.map((c) => (
                <button
                  key={c}
                  type="button"
                  className="bl-chainchip"
                  data-on={chain === c}
                  onClick={() => setChain(c)}
                >
                  <ChainMark chain={c} size={13} />
                  {chainMeta[c].label}
                </button>
              ))}
            </div>
            <button className="bl-btn bl-btn--lg" type="submit">
              Investigate <span aria-hidden="true">→</span>
            </button>
          </form>

          <button className="bl-sample" type="button" onClick={() => setCa(DEMO_CONTRACT)}>
            <span className="meta">Try $NOCK on Base</span>
            <span className="num bl-sample__addr">{DEMO_CONTRACT.slice(0, 18)}…</span>
          </button>
        </div>

        <div className="bl-hero__strip">
          <span className="meta">BASE · BLOCK 24,182,904</span>
          <span className="meta">TX / S · 41.2</span>
          <span className="meta">PROJECTS TRACKED · 12,480</span>
          <span className="meta bl-hero__scroll">SCROLL ↓</span>
        </div>
      </header>

      {/* ================= moon vs rug ================= */}
      <MoonRug />

      {/* ================= flow + coverage ================= */}
      <div id="process" />
      <div id="coverage" />
      <FlowSection />

      {/* ================= product intro ================= */}
      <section className="bl-intro" ref={introRef}>
        <div className="bl-intro__top">
          <h2 className="display d2 bl-intro__h">
            One contract address.
            <br />
            <span className="italic">A complete project investigation.</span>
          </h2>
          <p className="bl-intro__note">
            The score is the summary. The investigation is the product.
          </p>
        </div>

        <ol className="bl-index">
          {DIMENSIONS.map((d, i) => (
            <li
              key={d.k}
              className="bl-index__item"
              style={{
                opacity: introSeen ? 1 : 0,
                transform: introSeen ? 'none' : 'translate3d(0,8px,0)',
                transition: `opacity 380ms var(--ease) ${i * 45}ms, transform 380ms var(--ease) ${
                  i * 45
                }ms`,
              }}
            >
              <span className="bl-index__n meta">{String(i + 1).padStart(2, '0')}</span>
              <span className="bl-index__k">{d.k}</span>
              <span className="bl-index__d">{d.d}</span>
            </li>
          ))}
        </ol>

        <div className="bl-cta">
          <div className="bl-cta__arc" aria-hidden="true">
            <svg viewBox="0 0 400 200" preserveAspectRatio="none">
              <path d="M0,200 A200,200 0 0 1 400,200" fill="none" stroke="var(--rule)" strokeWidth="1" />
              <path d="M40,200 A160,160 0 0 1 360,200" fill="none" stroke="var(--rule-faint)" strokeWidth="1" />
            </svg>
          </div>
          <Link className="bl-btn bl-btn--xl" to="/app/new">
            Open Workspace <span aria-hidden="true">→</span>
          </Link>
          <p className="meta bl-cta__sub">No account required for the prototype</p>
        </div>
      </section>

      {/* ================= footer ================= */}
      <footer className="bl-foot">
        <Logo size={19} />
        <div className="bl-foot__cols">
          <span className="meta">Blockchain project intelligence</span>
          <span className="meta">Prototype · Front-end only · Data is illustrative</span>
        </div>
      </footer>
    </div>
  );
}
