# Deploy

One image, two targets. The warehouse is regenerated deterministically at startup, so there is **no
database to provision** anywhere.

## Security posture

- **Fail closed:** binding a non-loopback host without `TESSERA_API_TOKEN` refuses to start.
- When a token is set, every request needs `Authorization: Bearer <token>` (constant-time check);
  `/health` stays open for liveness probes.
- The API takes **natural-language questions, never SQL** — there is no user-controlled SQL path.
- Secrets (`TESSERA_API_TOKEN`, `TESSERA_SIGNING_KEY`) come from the environment / a secret store —
  never the image or the repo.

## The API

```bash
pip install -e ".[api,crypto]"
tessera serve                       # http://127.0.0.1:8080 — loopback is zero-config
curl -s localhost:8080/health
curl -s -X POST localhost:8080/ask -H 'Content-Type: application/json' \
  -d '{"question":"What was consolidated net revenue in 2025?","sign":true}'
```

| Endpoint | Purpose |
|---|---|
| `GET /health` | liveness + dataset info |
| `GET /metrics` | list certified metrics |
| `POST /ask` | resolve → verify (optional `route`, `sign`) |
| `POST /verify` | offline-verify a receipt |

## Cloud — Google Cloud Run

Scale-to-zero on the free tier, no DB to manage. See `deploy/cloudrun.sh`.

```bash
GCP_PROJECT=<project> GCP_REGION=us-central1 ./deploy/cloudrun.sh
```

The live demo runs this way: **[tessera.amitinfotech.net](https://tessera.amitinfotech.net)** (Vercel
frontend) → Cloud Run backend.

## Air-gapped — Compose / k3s

Inference is served by an on-box Ollama on an `internal: true` network with **no internet egress**;
the API is published only on the host loopback.

```bash
export TESSERA_API_TOKEN=$(openssl rand -hex 16)
docker compose -f deploy/docker-compose.airgapped.yml up --build
```

The same `tessera.api` runs unchanged on k3s/Podman for a real cluster — "your VPC or fully offline."

## The web UI

A minimal Next.js front end ([`web/`](https://github.com/amitpatole/tessera/tree/main/web)) — three
components (ask / answer + verdict / evidence drawer). The browser only calls same-origin `/api/*`
proxies that hold the token server-side, so it never reaches the client. Deploy to Vercel with
`TESSERA_API_URL` + `TESSERA_API_TOKEN` set.
