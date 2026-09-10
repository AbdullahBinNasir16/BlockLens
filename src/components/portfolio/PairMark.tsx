import type { Trade, TradeKind } from '../../data/types';

/* The pair is the identity of a trade in this book. Most of these tokens
   have no logo worth drawing, and for the stock-paired ones the quote
   asset is half the joke — so the mark is typographic: the token in the
   serif, the thing it is priced in beside it. */

export const KIND_LABEL: Record<TradeKind, string> = {
  meme: 'Memecoin',
  ai: 'AI',
  infra: 'Infra',
  defi: 'DeFi',
};

export function PairMark({
  trade,
  size = 'md',
}: {
  trade: Trade;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}) {
  const stock = trade.quote.kind === 'stock';
  return (
    <span className="bl-tpair" data-size={size} title={`${trade.ticker} / ${trade.quote.name}`}>
      <span className="bl-tpair__base">{trade.ticker}</span>
      <span className="bl-tpair__slash" aria-hidden="true" />
      <span className="bl-tpair__quote" data-stock={stock}>
        {trade.quote.ticker}
        {stock && (size === 'lg' || size === 'xl') && <span className="bl-tpair__tag">stock</span>}
      </span>
    </span>
  );
}

export function KindTag({ kind }: { kind: TradeKind }) {
  return (
    <span className="bl-ktag" data-kind={kind}>
      {KIND_LABEL[kind]}
    </span>
  );
}
