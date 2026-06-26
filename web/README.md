# Tessera — web UI

A minimal Next.js front end for Tessera: three components over the verified pipeline.

- **QuestionBar** — ask a question; toggle the cost cascade and a signed receipt.
- **AnswerCard** — the number + an independent verdict badge (PASS / WARN / FAIL).
- **EvidenceDrawer** — the executed SQL, the grounded issues, and a button to verify the receipt
  offline.

The browser only ever calls same-origin `/api/ask` and `/api/verify`; those server routes proxy to
the backend and hold the API token (`TESSERA_API_TOKEN`), so the token is never shipped to the client.

## Local

```bash
# 1) run the backend (in the repo root):  tessera serve         # http://127.0.0.1:8080
# 2) run the UI:
cp .env.example .env.local        # defaults already point at the local backend
npm install
npm run dev                       # http://localhost:3000
```

## Deploy (Vercel)

Set the project root to `web/`, and add two **server-side** env vars:

- `TESSERA_API_URL` = `https://api.tessera.amitinfotech.net`
- `TESSERA_API_TOKEN` = the token you set on Cloud Run

Custom domain: `tessera.amitinfotech.net`.

Styling reuses the shared "Warm Paper" design tokens; Tessera's accent is a desaturated ledger teal
(`--accent: #4f8a7b`).
