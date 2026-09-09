import { useEffect, useState } from 'react';
import { Navigate, useParams } from 'react-router-dom';
import { datasets } from '../data/projects';
import { ProjectProvider } from '../lib/project-context';
import { ProjectHeader } from '../components/research/ProjectHeader';
import { Overview } from '../components/research/Overview';
import { Fundamentals } from '../components/research/Fundamentals';
import { DeveloperSection } from '../components/research/DeveloperSection';
import { OnChainSection } from '../components/research/OnChainSection';
import { WalletSection } from '../components/research/WalletSection';
import { KolSection } from '../components/research/KolSection';
import { GithubSection } from '../components/research/GithubSection';
import { SocialSection } from '../components/research/SocialSection';
import { RoadmapSection } from '../components/research/RoadmapSection';
import { NarrativeSection } from '../components/research/NarrativeSection';
import { RiskSection } from '../components/research/RiskSection';
import { FinalAssessment } from '../components/research/FinalAssessment';

const INDEX = [
  { id: 'overview', n: '00', label: 'Overview' },
  { id: 'fundamentals', n: '01', label: 'Fundamentals' },
  { id: 'developer', n: '02', label: 'Developer' },
  { id: 'onchain', n: '03', label: 'On-Chain' },
  { id: 'wallets', n: '04', label: 'Wallets' },
  { id: 'kols', n: '05', label: 'KOLs' },
  { id: 'github', n: '06', label: 'GitHub' },
  { id: 'social', n: '07', label: 'Social' },
  { id: 'roadmap', n: '08', label: 'Roadmap' },
  { id: 'narrative', n: '09', label: 'Narrative' },
  { id: 'risk', n: '10', label: 'Risk' },
  { id: 'assessment', n: '11', label: 'Assessment' },
];

function ContentsRail() {
  const [active, setActive] = useState('overview');

  useEffect(() => {
    const els = INDEX.map((i) => document.getElementById(i.id)).filter(Boolean) as HTMLElement[];
    if (els.length === 0) return;

    const io = new IntersectionObserver(
      (entries) => {
        /* pick the entry nearest the top of the viewport that is on screen */
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: '-12% 0px -70% 0px', threshold: 0 }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <nav className="bl-contents" aria-label="Section index">
      {INDEX.map((i) => (
        <a
          key={i.id}
          href={`#${i.id}`}
          className="bl-contents__i"
          data-on={active === i.id}
          onClick={(e) => {
            e.preventDefault();
            document.getElementById(i.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }}
        >
          <span className="bl-contents__n">{i.n}</span>
          <span className="bl-contents__l">{i.label}</span>
          <span className="bl-contents__dash" aria-hidden="true" />
        </a>
      ))}
    </nav>
  );
}

export function ProjectIntelligence() {
  const { id } = useParams();
  /* an id we do not hold is never rendered as the default project */
  if (!id || !datasets[id]) {
    return <Navigate to={id ? `/app/token/${encodeURIComponent(id)}` : '/app/new'} replace />;
  }
  return (
    <ProjectProvider id={id} key={id}>
      <ResearchBody />
    </ProjectProvider>
  );
}

function ResearchBody() {
  return (
    <div className="bl-research">
      <ContentsRail />
      <div className="bl-research__body">
        <ProjectHeader />
        <Overview />
        <Fundamentals />
        <DeveloperSection />
        <OnChainSection />
        <WalletSection />
        <KolSection />
        <GithubSection />
        <SocialSection />
        <RoadmapSection />
        <NarrativeSection />
        <RiskSection />
        <FinalAssessment />
      </div>
    </div>
  );
}
