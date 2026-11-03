"""Generated from contract/blocklens.schema.json by scripts/contract.py. Do not edit:
change src/data/api.ts and run `npm run contract`."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, RootModel
from enum import Enum, StrEnum


class Model(RootModel[Any]):
    root: Any


class TrendingWindow(StrEnum):
    m5 = 'm5'
    h1 = 'h1'
    h6 = 'h6'
    h24 = 'h24'


class Change(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    m5: float
    h1: float
    h6: float
    h24: float


class Volume(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    m5: float
    h1: float
    h6: float
    h24: float


class Buys(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    m5: float
    h1: float
    h6: float
    h24: float


class Sells(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    m5: float
    h1: float
    h6: float
    h24: float


class Makers(BaseModel):
    """
    unique buyers + sellers, from GeckoTerminal; null where it gives none
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    m5: float | None
    h1: float | None
    h6: float | None
    h24: float | None


class TokenSecurity(BaseModel):
    """
    GoPlus token security, the parts the UI shows.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    holders: float | None
    top10Pct: float | None = Field(
        ..., description='share of supply held by the ten largest holders, percent'
    )
    honeypot: bool | None
    asOf: str


class Provenance(StrEnum):
    """
    Where a section's numbers come from. 'live'   — fetched from a public source and reproducible 'sample' — illustrative shape for the prototype, not a real finding
    """

    live = 'live'
    sample = 'sample'


class MarketPair(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    pool: str
    url: str
    dex: str
    quote: str
    price: float
    change24h: float
    volume24h: float
    buys24h: float
    sells24h: float
    liquidity: float
    marketCap: float
    fdv: float
    createdAt: float = Field(..., description='ms epoch')


class TokenMarket(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    name: str
    symbol: str
    logo: str | None = None
    website: str | None = None
    pairs: list[MarketPair] = Field(..., description='deepest first')
    asOf: str


class MarketSection(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    provenance: Provenance
    data: TokenMarket | None = Field(
        ..., description='null when DexScreener has no Base pair for the address'
    )
    error: str | None = None


class SecuritySection(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    provenance: Provenance
    data: TokenSecurity | None
    error: str | None = None


class RiskState(StrEnum):
    scored = 'scored'
    pending = 'pending'
    not_scored = 'not_scored'
    out_of_scope = 'out_of_scope'


class ModelCard(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    version: str
    target: str = Field(..., description='what the score predicts, in words')
    appliesTo: str = Field(
        ..., description='the population the model was trained to judge'
    )
    trainedOnLaunches: list[str]
    trainedOnTokens: float
    trainedAt: str = Field(..., description='date the model artifact was written')


class LaunchType(Enum):
    launchpad = 'launchpad'
    self_deployed = 'self-deployed'
    NoneType_None = None


class ForwardBand(BaseModel):
    """
    What happened, forward, to launches the model scored in the same band. This is the honest reading of a score: the model's raw probabilities are not calibrated forward (DECISIONS.md, Phase 8 result).
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    lo: float
    hi: float
    launches: float
    losses: float
    observed: float = Field(..., description='losses / launches')
    since: str


class Direction(StrEnum):
    raises = 'raises'
    lowers = 'lowers'
    neutral = 'neutral'


class Driver(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    feature: str
    label: str
    value: float
    display: str
    contribution: float = Field(..., description='additive, in log-odds')
    direction: Direction


class Symbols(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    symbol: str
    name: str


class SymbolsResponse(BaseModel):
    """
    Display names for a batch of tokens (DexScreener, cached server side).
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    provenance: Provenance
    symbols: dict[str, Symbols]


class ScreenerToken(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    symbol: str
    name: str
    launchedAt: float = Field(
        ..., description='ms epoch of the first swap BlockLens stored'
    )
    wallets: float


class FundingSource(StrEnum):
    fresh = 'fresh'
    cex = 'cex'
    bridge = 'bridge'
    cluster = 'cluster'
    unknown = 'unknown'


class Chain(StrEnum):
    ethereum = 'ethereum'
    base = 'base'
    solana = 'solana'
    bnb = 'bnb'


class UpstreamHealth(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    ok: bool
    latencyMs: float | None
    error: str | None = None
    checkedAt: str
    calls: float = Field(
        ..., description='calls made to this source since the API started'
    )
    cacheHits: float


class Database(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    ok: bool
    error: str | None = None


class Model1(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    loaded: bool
    version: str | None


class Scorer(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    running: bool
    lastRun: str | None
    lastError: str | None
    scannedToBlock: float | None
    tracked: float


class Alerts(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    enabled: bool
    sent: float
    lastError: str | None


class HealthResponse(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    ok: bool
    database: Database
    model: Model1
    scorer: Scorer
    alerts: Alerts
    upstream: dict[str, UpstreamHealth]


class TrendingPool(BaseModel):
    """
    One row per token: the highest-ranked pool stands for it.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    rank: float
    pool: str
    url: str
    dex: str
    token: str
    name: str
    symbol: str
    quote: str
    logo: str | None = None
    price: float
    change: Change
    volume: Volume
    buys: Buys
    sells: Sells
    makers: Makers = Field(
        ...,
        description='unique buyers + sellers, from GeckoTerminal; null where it gives none',
    )
    liquidity: float
    marketCap: float
    fdv: float
    createdAt: float = Field(..., description='ms epoch')
    holders: TokenSecurity | None


class TrendingResponse(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    provenance: Provenance
    window: TrendingWindow
    asOf: str = Field(..., description='ISO time the ranking was fetched upstream')
    stale: bool = Field(
        ...,
        description='true when GeckoTerminal is throttling and the last good ranking is served',
    )
    pools: list[TrendingPool]


class RiskScore(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    risk: float = Field(
        ...,
        description="the model's raw output: a ranking, not a calibrated probability",
    )
    launchType: LaunchType | None
    launchTs: str
    scoredAt: str
    band: ForwardBand | None
    drivers: list[Driver]
    rest: float = Field(
        ...,
        description='what every feature outside `drivers` contributed, together (log-odds)',
    )
    baseRate: float = Field(
        ..., description="the model's score for a launch about which nothing is known"
    )


class WalletProjectPosition(BaseModel):
    """
    One wallet's position in one project.

    Money is stored as what actually moved — spent, taken out, still held — and never as a pre-computed PnL. Every figure the screener filters on is derived from these, so the prototype filters the way a backend would.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    projectId: str
    chain: Chain
    firstBuy: float = Field(..., description='ms epoch of the first buy')
    lastSell: float | None = Field(
        ...,
        description='ms epoch of the last sell; null while the position is still open',
    )
    buys: float
    sells: float
    invested: float = Field(..., description='USD spent acquiring the position')
    soldFraction: float = Field(
        ..., description='share of the position that has been sold, 0-1'
    )
    proceeds: float = Field(..., description='USD received from those sells')
    remainingValue: float = Field(..., description='USD value of what is still held')
    entryDelay: float = Field(
        ...,
        description="ms between the project's first pair activity and this wallet's first buy",
    )
    averagedDown: bool
    soldFirstPump: bool
    wentToZero: bool
    honeypot: bool
    observedUntil: float | None = Field(
        None,
        description='ms epoch the record stops observing this position. The live store holds each launch\'s first 24 hours, so an open position there is "still held at the end of what was seen", and is measured to here, never to the corpus clock. Absent: observed to the corpus clock.',
    )


class TokenRiskResponse(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    provenance: Provenance
    state: RiskState
    reason: str = Field(
        ..., description='why there is or is not a score, in a sentence a user can read'
    )
    model: ModelCard
    score: RiskScore | None


class WalletRecord(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    label: str | None = Field(None, description='a known identity, when one exists')
    ens: str | None = None
    firstSeen: float = Field(
        ..., description='ms epoch the wallet first appeared on chain'
    )
    fundingSource: FundingSource
    clusterSize: float = Field(
        ..., description='wallets funded from the same origin, including this one'
    )
    smartMoney: bool
    insiderLinked: bool
    positions: list[WalletProjectPosition]


class ProjectLiveResponse(BaseModel):
    """
    The live half of a token page. The research sections are not here: they are sample, held by the front end, and badged as such.
    """

    model_config = ConfigDict(
        extra='forbid',
    )
    address: str
    market: MarketSection
    security: SecuritySection
    risk: TokenRiskResponse


class ScreenerResponse(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    provenance: Provenance
    asOf: str
    unit: Literal['USD'] = Field(
        ...,
        description="positions' money: ETH amounts from the store, converted at each trade's own day's ETH close (GeckoTerminal daily candles, WETH/USDC on Base)",
    )
    tokens: list[ScreenerToken]
    contracts: list[str] = Field(
        ...,
        description='the contracts asked for; wallets are those with a position in one of them, with all their positions. Empty when only the index was asked.',
    )
    wallets: list[WalletRecord]
