# politics-dashboard

A self-hosted dashboard that aggregates political and government news from RSS
feeds, summarizes each story with an LLM, generates a 24-hour digest grouped
into thematic categories, and (optionally) shows live X/Twitter posts and
per-account summaries via [Nitter](https://github.com/zedeus/nitter).

You configure your own feeds, your own X handles, and your own LLM provider
(local Ollama, Anthropic, OpenAI, vLLM, LM Studio — anything OpenAI-compatible
works). Nothing is hardcoded to a particular news source or political angle.

![screenshot placeholder](docs/screenshot.png)

## Features

- **Pluggable LLM** — point at local Ollama, OpenAI, Anthropic, vLLM, LM Studio,
  Together, Groq. Two providers built in: `openai_compatible` and `anthropic`.
- **Pluggable feeds** — direct RSS/Atom URLs, or a FreshRSS instance via the
  Greader API if you already curate feeds there.
- **Configurable categories** — name them whatever fits your beat. They become
  filter buttons in the UI and sections in the digest.
- **Per-article AI summary** — 2–3 sentences, generated in the background.
- **24-hour digest** — refreshed hourly, structured into thematic sections
  (Executive Branch, Congress, Courts, Foreign Policy, etc.) with a "Bottom
  Line" closer.
- **Optional X/Twitter panel** — live embed via your own Nitter instance, plus
  3-hour AI summary per handle.
- **No tracking, no telemetry, no auth wall.** Run it on your laptop or behind
  whatever auth you already use.

## Quick start (docker-compose)

```bash
git clone https://github.com/<you>/politics-dashboard.git
cd politics-dashboard
cp config.example.yaml config.yaml
cp .env.example .env

# Edit config.yaml: pick LLM provider, add your RSS feeds.
# Edit .env: add API keys (or leave blank for local Ollama).

docker compose up -d
```

Open <http://localhost:8080>.

## Configuration

All structure (LLM provider, feeds, categories, refresh intervals) lives in
`config.yaml`. All secrets and per-deploy overrides live in environment
variables. See [`config.example.yaml`](config.example.yaml) for the full
schema with comments.

### LLM providers

```yaml
# Local Ollama (default)
llm:
  provider: openai_compatible
  base_url: http://ollama:11434/v1
  model: llama3.1:8b
  api_key_env: LLM_API_KEY        # leave LLM_API_KEY unset for local Ollama

# OpenAI
llm:
  provider: openai_compatible
  base_url: https://api.openai.com/v1
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY

# Anthropic
llm:
  provider: anthropic
  base_url: https://api.anthropic.com
  model: claude-haiku-4-5
  api_key_env: ANTHROPIC_API_KEY
```

### Feeds

Direct RSS — zero infrastructure:

```yaml
feeds:
  source: rss
  categories:
    news:
      label: News
      urls:
        - https://feeds.reuters.com/reuters/topNews
        - https://feeds.washingtonpost.com/rss/politics
    government:
      label: Government
      urls:
        - https://www.whitehouse.gov/feed/
```

Or, if you already run [FreshRSS](https://www.freshrss.org/) and curate feeds
there:

```yaml
feeds:
  source: freshrss
  freshrss:
    url: https://freshrss.example.com/api/greader.php
    username: api-user
    password_env: FRESHRSS_API_PASSWORD
  categories:
    news:
      label: News
      freshrss_label: News           # FreshRSS tag/label name
    government:
      label: Government
      freshrss_label: Government
```

### Twitter / X (optional)

The X panel uses [Nitter](https://github.com/zedeus/nitter), which you must
deploy yourself. Public Nitter instances rate-limit aggressively — running
your own is the only reliable option.

Once you have Nitter running:

```yaml
twitter:
  enabled: true
  nitter_url: http://nitter:8080      # backend (API ↔ Nitter)
  categories:
    politics:
      label: Politics
      handles: [benshapiro, anncoulter]
    government:
      label: Government
      handles: [POTUS, WhiteHouse]
```

The frontend iframe needs a separate URL because the browser, not the API,
loads it. Set `VITE_NITTER_EMBED_BASE` (a build-time env var) to your
publicly-reachable Nitter URL.

To override handle lists from environment (handy for Kubernetes Secrets):

```yaml
twitter:
  handles_env_prefix: X
```

Then `X_POLITICS=foo,bar` and `X_GOVERNMENT=baz` will replace the YAML lists
at startup.

## Architecture

```
┌──────────────┐    ┌──────────────────────────────┐    ┌────────────┐
│  RSS feeds   │───►│  api  ── feeds/poller        │    │            │
└──────────────┘    │       ── per-article summary │───►│   LLM      │
                    │       ── 24h digest          │    │ (Ollama,   │
┌──────────────┐    │       ── twitter summaries   │    │  OpenAI,   │
│  FreshRSS    │───►│                              │    │  Anthropic)│
└──────────────┘    │                              │    └────────────┘
                    │                              │
┌──────────────┐    │                              │    ┌────────────┐
│   Nitter     │◄───┤  twitter/                    │◄───┤  browser   │
│  (your own)  │    │                              │    │   iframe   │
└──────────────┘    └──────────────┬───────────────┘    └────────────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │  ui (nginx) │
                            └─────────────┘
```

State is in-memory only. Articles refresh every 15 minutes by default;
digests every hour; Twitter summaries every 3 hours. Restart the API and you
re-poll from the source feeds.

## API

| Method | Path                          | Purpose                                |
| ------ | ----------------------------- | -------------------------------------- |
| GET    | `/config`                     | Public config consumed by the UI       |
| GET    | `/articles?category=&limit=`  | Recent articles with summaries         |
| GET    | `/accounts`                   | X handles per category                 |
| GET    | `/accounts/summaries`         | Per-handle summaries                   |
| GET    | `/accounts/digest`            | 24-hour digest                         |
| POST   | `/accounts/digest/refresh`    | Force a digest regen                   |
| POST   | `/refresh`                    | Force an article refresh               |
| GET    | `/health`                     | Liveness check                         |

## Kubernetes deployment

Example manifests live in [`deploy/kubernetes/`](deploy/kubernetes/). They
assume:

- A `Secret` named `politics-secrets` carries `LLM_API_KEY`,
  `FRESHRSS_API_PASSWORD`, and any `X_*` handle overrides.
- A `ConfigMap` named `politics-config` carries `config.yaml`.

Wire your own ingress / Gateway / auth in front of the `politics-ui` Service.

## Development

```bash
# API
cd api && pip install -r requirements.txt
CONFIG_PATH=../config.yaml uvicorn app.main:app --reload

# UI
cd ui && npm install && npm run dev
```

The Vite dev server proxies `/api/*` to `http://localhost:8000` (configured in
`vite.config.ts`).

## License

MIT — see [LICENSE](LICENSE).
