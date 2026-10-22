# Hosting BlockLens

Two routes. Both use what CD already publishes; neither needs a code change.

## Route A: Render, from the blueprint (fastest to a public URL)

1. Create a Render account (free) at render.com and connect the GitHub
   account that can see the repository.
2. New → Blueprint → select `AbdullahBinNasir16/BlockLens` → Apply.
   `render.yaml` creates three things: a PostgreSQL database (free tier, 90
   days), the API as a Docker web service, and the static site.
3. Wait for the first deploy (about 10 minutes: the API image installs
   scikit-learn and shap). The site is at `https://blocklens-web.onrender.com`,
   the API at `https://blocklens-api.onrender.com/api/health`.
4. Optional: on the API service, add `TELEGRAM_BOT_TOKEN` and
   `TELEGRAM_CHAT_ID` for alerts.
5. Optional, to redeploy on every merge to `main`: copy the API service's
   Deploy Hook URL (Settings → Deploy Hook) into the repository secret
   `RENDER_DEPLOY_HOOK`. The CD workflow already calls it.

Cost: the API must be always-on for the forward test, which is Render's
starter plan (about US$7 a month at the time of writing). The static site
and the database are free. A free API instance would sleep between visits
and miss launches.

If the API service name differs, edit the `/api/*` rewrite destination in
`render.yaml` to match.

## Route A2: Vercel for the site, Render for the API

Vercel hosts the static site for free and cannot host the API (a
long-running process with a database). `vercel.json` is in the repository:

1. On vercel.com, sign in with GitHub → Add New Project → import the
   repository → Deploy. Framework and output directory are read from
   `vercel.json`; the rewrites send `/api` to the Render API and the
   three public sources to their origins, so the app keeps one origin.
2. Create the API and database on Render as in Route A (steps 1--3); the
   `blocklens-web` static service there can be deleted if Vercel serves it.
3. If the API's URL is not `blocklens-api.onrender.com`, change the `/api`
   destination in `vercel.json` and redeploy.

Note: server-sent events (`/api/stream`) through Vercel's rewrite work but
may reconnect periodically; the page tolerates that and keeps polling.

## Route B: any Linux VM with Docker (cheapest always-on)

```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/AbdullahBinNasir16/BlockLens && cd BlockLens
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

The product is on port 8080; put Caddy or nginx in front for HTTPS. The
images are pulled from GHCR (public read on a private repository needs a
GHCR token: `docker login ghcr.io`). `restart: unless-stopped` survives
reboots. Any provider's smallest VM is enough (2 GB RAM).

## Before the demo, either route

- Open `/api/health`: `last_run` must be within the last two minutes.
- Open `/app/launches`: the state must read Live and Push on.
- Open `/app/model`: no outage in the last day.
