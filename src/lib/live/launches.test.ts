import { describe, expect, it } from 'vitest';
import { riskBand } from './launches';

/* The live feed's band thresholds are the ones printed on the Fresh Launches
   page: 0.5 is "flagged" in the forward protocol, 0.2 is the paper agent's
   buy ceiling (DECISIONS.md, Phases 8 and 9). */
describe('riskBand (buyer-loss probability)', () => {
  it('flags at 0.5 and above', () => {
    expect(riskBand(0.5)).toBe('high');
    expect(riskBand(0.99)).toBe('high');
  });
  it('is medium from 0.2 up to 0.5', () => {
    expect(riskBand(0.2)).toBe('medium');
    expect(riskBand(0.49)).toBe('medium');
  });
  it('is low below the agent ceiling', () => {
    expect(riskBand(0)).toBe('low');
    expect(riskBand(0.19)).toBe('low');
  });
});
