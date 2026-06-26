#!/usr/bin/env bash
# Deploy the Tessera API to Google Cloud Run (the locked free cloud target).
#
# Prereqs (run once, interactively):  gcloud auth login  &&  gcloud config set project <PROJECT>
# Secrets (run once): create the API token + signing key as Secret Manager secrets — see deploy/README.md.
#
# Usage:  GCP_PROJECT=my-proj GCP_REGION=us-central1 ./deploy/cloudrun.sh
set -euo pipefail

PROJECT="${GCP_PROJECT:?set GCP_PROJECT}"
REGION="${GCP_REGION:-us-central1}"
SERVICE="${SERVICE:-tessera}"

echo "Deploying '${SERVICE}' to Cloud Run (project=${PROJECT}, region=${REGION})…"

# Builds from the repo Dockerfile via Cloud Build, then deploys. The app fails closed unless
# TESSERA_API_TOKEN is present, so it is injected from Secret Manager (never baked into the image).
gcloud run deploy "${SERVICE}" \
  --source . \
  --project "${PROJECT}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 --memory 512Mi \
  --max-instances 3 --min-instances 0 \
  --set-env-vars "TESSERA_BIND_HOST=0.0.0.0" \
  --set-secrets "TESSERA_API_TOKEN=tessera-api-token:latest,TESSERA_SIGNING_KEY=tessera-signing-key:latest"

URL="$(gcloud run services describe "${SERVICE}" --project "${PROJECT}" --region "${REGION}" \
  --format='value(status.url)')"
echo "Deployed: ${URL}"
echo "Smoke test:  curl -s ${URL}/health"
