# OmniNode Docker Stack

This repository includes a local `compose.yaml` so the team can start a minimal
OmniNode-compatible stack directly from `OmniCursor`.

## What it starts

Default `docker compose up -d --build` starts:

- PostgreSQL
- Redpanda
- Valkey
- `intelligence-reducer`
- `intelligence-orchestrator`
- `quality-scoring-compute`

Optional memory profile:

```bash
docker compose --profile memory up -d --build
```

That adds:

- Qdrant
- Memgraph
- Kreuzberg parser

## Why this compose builds from GitHub

The stack uses Docker Compose remote Git contexts for `omniintelligence` so we
can keep `OmniCursor` small and still build upstream services from
`OmniNode-ai/*` repositories.

You can run the stack with built-in defaults and no `.env` file at all:

```bash
docker compose up -d --build
```

Use `.env` only when you want to pin refs, change ports, or override local
credentials:

```bash
cp .env.omninode.example .env
# Change OMNIINTELLIGENCE_REF from main to a tag or commit SHA if you want.
docker compose up -d --build
```

## Useful commands

```bash
# Start the default stack
docker compose up -d --build

# Add memory services too
docker compose --profile memory up -d --build

# View logs
docker compose logs -f intelligence-orchestrator

# Stop everything
docker compose down

# Stop and remove named volumes
docker compose down -v
```

## Important limitation

This stack is meant for local integration work from `OmniCursor`. It does not
yet replace the full ONEX runtime wiring from `omnibase_infra`. Upstream
`omniintelligence` documents that the standalone node containers start in stub
mode and full event-driven execution depends on `RuntimeHostProcess`.

In practice:

- This stack is good for local service bring-up, smoke tests, and dependency
  alignment.
- If you later need full ONEX runtime behavior, the next step is a custom
  runtime image that installs both `omnibase_infra` and `omniintelligence`
  together.
