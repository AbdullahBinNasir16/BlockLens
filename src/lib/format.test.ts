import { describe, expect, it } from 'vitest';
import { compact, duration, price, riskBand, shortAddr, signedUsd } from './format';

describe('compact', () => {
  it('scales to K, M and B', () => {
    expect(compact(950)).toBe('950');
    expect(compact(1_500)).toBe('1.5K');
    expect(compact(2_000_000)).toBe('2M');
    expect(compact(3_250_000_000)).toBe('3.25B');
  });
});

describe('price', () => {
  it('keeps more decimals as the price gets smaller', () => {
    expect(price(0)).toBe('$0');
    expect(price(12.345)).toBe('$12.35');
    expect(price(0.5)).toBe('$0.5000');
    expect(price(0.00012)).toBe('$0.00012');
  });
  it('writes a dust price out in full rather than with subscript zeros', () => {
    expect(price(0.00000042)).toBe('$0.00000042');
  });
});

describe('shortAddr', () => {
  it('elides the middle of a contract address', () => {
    expect(shortAddr('0x9b5e5a3f2a5d4b4a0b8c6e2d1a1f0e9c8b7a1722')).toBe('0x9b5e…1722');
  });
  it('leaves a short string alone', () => {
    expect(shortAddr('0xabc')).toBe('0xabc');
  });
});

describe('duration', () => {
  it('picks the largest unit that still reads precisely', () => {
    expect(duration(0.5)).toBe('30s');
    expect(duration(2.5)).toBe('2.5m');
    expect(duration(90)).toBe('1h 30m');
    expect(duration(60 * 24 * 3)).toBe('3d');
    expect(duration(60 * 24 * 90)).toBe('3.0mo');
  });
});

describe('signedUsd', () => {
  it('always carries a sign', () => {
    expect(signedUsd(2500)).toBe('+$2.5K');
    expect(signedUsd(-120)).toBe('−$120');
  });
});

describe('riskBand', () => {
  it('maps a 0-100 risk score to a band', () => {
    expect(riskBand(10)).toBe('low');
    expect(riskBand(40)).toBe('medium');
    expect(riskBand(65)).toBe('high');
  });
});
