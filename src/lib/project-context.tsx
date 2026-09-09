import { createContext, useContext } from 'react';
import type { ProjectDataset, Provenance } from '../data/types';
import { getDataset } from '../data/projects';

const Ctx = createContext<ProjectDataset>(getDataset(undefined));

export function ProjectProvider({
  id,
  children,
}: {
  id: string | undefined;
  children: React.ReactNode;
}) {
  return <Ctx.Provider value={getDataset(id)}>{children}</Ctx.Provider>;
}

/** The dataset for the project currently being viewed. */
export function useProject(): ProjectDataset {
  return useContext(Ctx);
}

/** Whether a given section's figures are sourced or illustrative. */
export function useProvenance(section: string): Provenance {
  return useContext(Ctx).provenance[section] ?? 'sample';
}
