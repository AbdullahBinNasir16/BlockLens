# Running BlockLens from nothing

This starts the whole product on a clean machine: database, API and the
production front end. The steps are exactly what CI's **"Clean machine ·
docker compose up"** job runs on a fresh runner, so if one is missing, that
job fails.

## You need

- Docker with Compose v2 (`docker compose version` prints 2.x).
- Git.
- Internet access. The API reads the Base chain and three public market
  sources. None of them needs a key.

## 1. Get the code

```sh
git clone https://github.com/AbdullahBinNasir16/BlockLens.git
cd BlockLens
```

## 2. Start it

```sh
docker compose up --build
```

The first build takes a few minutes. When the logs show
`Uvicorn running on http://0.0.0.0:8000`, the stack is up.

## 3. Open it

- The app: <http://localhost:8080>
- The health check: <http://localhost:8080/api/health>. It reports:
  - database connectivity;
  - the loaded model version;
  - whether the scorer is running;
  - whether each market source is reachable;
  - how many calls have been made to each source.

## What a fresh install shows

The database starts empty, so some screens begin with less, and they say so:

- **Trending Tokens** is live at once.
- **Fresh Launches** fills as new launches reach their five-minute mark,
  about 25 an hour. If `BLOCKLENS_LIVE=0`, nothing new is scored.
- **Token pages** show live market and contract data. The model's view
  reads "Outside the model's scope" for every token the feed has not yet
  scored at its own minute 5.
- **The Wallet Screener** needs the research store's labelled launches.
  - Without them it shows its sample corpus, under a "Sample data" badge
    that gives the reason.
  - To screen real wallets, run against a store that holds the research
    data (see `backend/README.md`).
- **Model Health and the Paper Agent** start empty. They fill as outcomes
  resolve at hour 6.

## Settings

Every setting is an environment variable with a working default, so step 2
needs none. To change one:

1. Copy `.env.example` to `.env`.
2. Set the variables you need. Compose reads `.env` automatically.

Common ones:

| Variable | Default | What it does |
|---|---|---|
| `WEB_PORT` | 8080 | the port the app is served on |
| `BLOCKLENS_LIVE` | 1 | `0` serves the UI without polling the chain |
| `VITE_API_URL` | empty (same origin) | build the front end against an API elsewhere |
| `VITE_LIVE_<SCREEN>` | live | `0` puts that screen on its sample data |
| `UPSTREAM_MAX_CALLS_PER_DAY` | 50000 | daily ceiling on calls to the market sources |

No key is needed, and none is in the repository.

## Stop, reset

```sh
docker compose down        # stop; keeps the database
docker compose down -v     # stop and delete the database and API state
```

## Without Docker (development)

- PostgreSQL 16 on `127.0.0.1:5433`.
- The API: `cd backend && pip install -e ".[dev]" && python -m alembic upgrade head && uvicorn blocklens.api.app:app --port 8000`
- The front end: `npm ci && npm run dev`, which proxies `/api` to port 8000.

For a production build against a local API:

```sh
VITE_API_URL=http://127.0.0.1:8000 npm run build
npx vite preview
```
