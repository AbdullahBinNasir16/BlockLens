/* Generate the API contract from src/data/api.ts.

     node scripts/contract.mjs           write contract/blocklens.schema.json
     node scripts/contract.mjs --check   exit 1 if the committed schema has drifted

   The backend half (Pydantic models) is generated from the schema by
   `backend/scripts/contract.py`; `npm run contract` runs both. */
import { readFileSync, writeFileSync } from 'node:fs';
import { createGenerator } from 'ts-json-schema-generator';

export const OUT = 'contract/blocklens.schema.json';

export function generate() {
  const schema = createGenerator({
    path: 'src/data/api.ts',
    tsconfig: 'tsconfig.json',
    type: '*',
    expose: 'export',
    topRef: true,
    skipTypeCheck: true,
  }).createSchema('*');
  // Only the types api.ts declares or references: tsconfig pulls in the
  // whole program, and the contract must not grow with it.
  return JSON.stringify(schema, null, 2) + '\n';
}

const check = process.argv.includes('--check');
const fresh = generate();
if (check) {
  const committed = readFileSync(OUT, 'utf8').replace(/\r\n/g, '\n');
  if (committed !== fresh) {
    console.error(`${OUT} is out of date: run npm run contract`);
    process.exit(1);
  }
  console.log(`${OUT} is up to date`);
} else {
  writeFileSync(OUT, fresh);
  console.log(`wrote ${OUT}`);
}
