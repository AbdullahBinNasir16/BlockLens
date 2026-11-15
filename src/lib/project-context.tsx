import { createContext, useContext } from 'react';
import type { ProjectDataset, Provenance } from '../data/types';
import type { ProjectLiveResponse } from '../data/api';
import { getDataset } from '../data/projects';
import { type Live, useLive } from './api';

/* The case-study page is genuinely mixed (Phase 7): its market figures and
   the model's view are live, from the API; its research sections are held
   here and are sample. Within one section the two never mix. */

/** When the three case studies' sourced figures were captured. Anything from
 *  the data files is a snapshot of that day, not live, and is badged so. */
export const SNAPSHOT_DATE = '9 Sep 2026';

interface Ctx {
  dataset: ProjectDataset;
  live: Live<ProjectLiveResponse | null>;
}

const NO_LIVE: Live<ProjectLiveResponse | null> = {
  data: null,
  provenance: 'sample',
  reason: 'not loaded',
  loading: false,
  updatedAt: 0,
};

const C = createContext<Ctx>({ dataset: getDataset(undefined), live: NO_LIVE });

export function ProjectProvider({
  id,
  children,
}: {
  id: string | undefined;
  children: React.ReactNode;
}) {
  const dataset = getDataset(id);
  const live = useLive<ProjectLiveResponse | null>(
    'project',
    `/api/project/${dataset.project.contract.toLowerCase()}`,
    null,
    60_000
  );
  return <C.Provider value={{ dataset, live }}>{children}</C.Provider>;
}

/** The dataset for the project currently being viewed. */
export function useProject(): ProjectDataset {
  return useContext(C).dataset;
}

/** The live half of the page, from `/api/project`. */
export function useProjectLive(): Live<ProjectLiveResponse | null> {
  return useContext(C).live;
}

/** Every research section is sample in Phase 7's sense: not live. Those whose
 *  figures were sourced from public data are a dated snapshot; the rest are
 *  illustrative. Both are badged on the section. */
export function useProvenance(_section: string): Provenance {
  return 'sample';
}

export function useSampleReason(section: string): string {
  const sourced = useContext(C).dataset.provenance[section] === 'live';
  return sourced ? `snapshot of ${SNAPSHOT_DATE}, not live` : 'illustrative, not findings';
}
