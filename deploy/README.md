# Deploying Tessera

One image (`../Dockerfile`), two targets. The warehouse is regenerated deterministically at startup,
so **there is no database to provision** anywhere.

Security posture (enforced in `tessera.api.security`):
- The app **fails closed**: binding a non-loopback host without `TESSERA_API_TOKEN` refuses to start.
- When a token is set, every request needs `Authorization: Bearer <token>` (constant-time check).
  `/health` stays open for liveness probes.
- The API takes **natural-language questions, never SQL** — there is no user-controlled SQL path.
- Secrets (`TESSERA_API_TOKEN`, `TESSERA_SIGNING_KEY`) come from the environment / a secret store —
  never the image or the repo.

---

## Cloud target — Google Cloud Run (the locked free demo)

One-time, interactive (needs your Google account):

```bash
gcloud auth login
gcloud config set project <YOUR_PROJECT>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

# Create the two secrets (run once):
printf '%s' "$(openssl rand -hex 16)" | gcloud secrets create tessera-api-token   --data-file=-
printf '%s' "$(openssl rand -hex 32)" | gcloud secrets create tessera-signing-key --data-file=-
```

Then deploy (repeatable):

```bash
GCP_PROJECT=<YOUR_PROJECT> GCP_REGION=us-central1 ./deploy/cloudrun.sh
```

Map the custom domain to `api.tessera.amitinfotech.net` (Cloud Run domain mapping, or a CNAME in the
Cloudflare DNS for `amitinfotech.net`). Verify the live deploy serves the change:

```bash
curl -s https://api.tessera.amitinfotech.net/health
curl -s -X POST https://api.tessera.amitinfotech.net/ask \
  -H "Authorization: Bearer $(gcloud secrets versions access latest --secret=tessera-api-token)" \
  -H 'Content-Type: application/json' \
  -d '{"question":"What was consolidated net revenue in 2025?"}'
```

---

## Air-gapped target — Docker Compose (illustrates the on-prem deployment)

Inference is served by an on-box Ollama on an `internal: true` network with no internet egress; the
API is published only on the host loopback.

```bash
export TESSERA_API_TOKEN=$(openssl rand -hex 16)
docker compose -f deploy/docker-compose.airgapped.yml up --build
# (optional) pull a local model into the on-box Ollama:
docker compose -f deploy/docker-compose.airgapped.yml exec ollama ollama pull llama3.1

curl -s http://127.0.0.1:8080/health
curl -s -X POST http://127.0.0.1:8080/ask \
  -H "Authorization: Bearer ${TESSERA_API_TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{"question":"What was consolidated net revenue in 2025?"}'
```

The same `tessera.api` runs unchanged on k3s/Podman for a real cluster; this Compose file is the
minimal, runnable illustration of "your VPC or fully offline."
