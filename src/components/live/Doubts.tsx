/* Plausibility checks the third-party figures failed: shown beside them,
   in words, as a reason to doubt them. Not a finding about the token. */
export function Doubts({ doubts }: { doubts: string[] }) {
  if (!doubts.length) return null;
  return (
    <p className="bl-doubts" role="note">
      <strong>Treat these figures with doubt.</strong> They are the market source's own numbers, and they fail{' '}
      {doubts.length === 1 ? 'a plausibility check' : 'plausibility checks'}: {doubts.join('; ')}. BlockLens shows
      them as reported and does not correct them.
    </p>
  );
}
