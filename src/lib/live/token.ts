/* Address helpers for token pages. The market lookup itself moved server
   side in Phase 7 (`/api/project/{address}`, backend/blocklens/api/market.py). */

export const isEvmAddress = (a: string) => /^0x[0-9a-fA-F]{40}$/.test(a.trim());
