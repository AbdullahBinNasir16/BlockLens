import { describe, expect, it } from 'vitest';
import { DEFAULT_PROJECT, datasets, findByContract, getDataset, projectIds } from './index';

describe('project registry', () => {
  it('holds the three researched projects', () => {
    expect(projectIds.sort()).toEqual(['dot', 'nockchain', 'sibyl']);
  });

  it('resolves a pasted contract regardless of letter case or whitespace', () => {
    for (const d of Object.values(datasets)) {
      const c = d.project.contract;
      expect(findByContract(c)?.project.id).toBe(d.project.id);
      expect(findByContract(`  ${c.toUpperCase()}  `)?.project.id).toBe(d.project.id);
    }
  });

  it('returns nothing for an address it has not researched', () => {
    expect(findByContract('0x' + '0'.repeat(40))).toBeUndefined();
  });

  it('falls back to the default project for an unknown id', () => {
    expect(getDataset('nope').project.id).toBe(DEFAULT_PROJECT);
    expect(getDataset(undefined).project.id).toBe(DEFAULT_PROJECT);
  });
});
