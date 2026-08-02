# How to deploy this project

This project has **two parts** you deploy separately:

| What | Where | What it is |
| --- | --- | --- |
| Chat website (UI) | **Vercel** | Next.js app in the `frontend/` folder |
| API (answers questions) | **Railway** | FastAPI app built from the root `Dockerfile` |
| Corpus refresh (optional) | **GitHub Actions** | Daily job (10:00 AM IST) that updates fund data |

```
User opens the Vercel site
        │
        │  asks a question (POST /ask)
        ▼
Railway API  →  reads baked-in fund index  →  Groq (GROQ_API_KEY)
        │
        ▼
Answer shown in the browser
```

You need accounts on **GitHub**, **Railway**, **Vercel**, and a **Groq** API key.

---

## Step 0 — Put the repo on GitHub

1. Push this project to a GitHub repository (private or public is fine).
2. Do **not** commit `.env` or any API keys.

---

## Step 1 — Prepare the fund data (required before Railway)

Railway builds a Docker image that **must** include the processed corpus and search index. Without these files, the build fails on purpose.

Needed files:

- `data/processed/chunks.jsonl`
- `data/index/bm25.pkl`
- `data/index/index_manifest.json`
- `data/index/dense_vectors.pkl` **or** `data/index/chroma/`

These folders are normally gitignored. Use **one** of these options:

### Option A — GitHub Actions (recommended)

1. In GitHub: **Actions** → **corpus-refresh** → **Run workflow**.
2. Wait until it finishes successfully (it force-commits the data files).
3. Deploy Railway from that updated commit.

### Option B — Build locally, then force-add

```bash
make refresh
# or: process + index your usual way

git add -f data/processed data/index
git commit -m "Add corpus artifacts for Railway deploy"
git push
```

Never commit `.env`.

---

## Step 2 — Deploy the backend on Railway

1. Go to [railway.app](https://railway.app) and sign in (GitHub login works well).
2. **New Project** → **Deploy from GitHub repo** → pick this repository.
3. Railway should detect the root `Dockerfile` (see `railway.toml`). If asked, choose Dockerfile builder.
4. Open the service → **Variables** and set:

| Variable | Required? | What to put |
| --- | --- | --- |
| `GROQ_API_KEY` | **Yes** | Your Groq API key |
| `CORS_ORIGINS` | **Yes** | Your Vercel site URL(s), comma-separated, no trailing slash. Example: `https://mf-faq.vercel.app` |
| `MF_RATE_LIMIT_PER_HOUR` | No | Defaults to `30` asks per IP per hour |

`PORT` and `MF_HEALTH_STRICT=1` are handled by Railway / the Docker image. You usually do not set them yourself.

5. Deploy and wait for the build to finish (first build can take several minutes — it installs Python deps and warms embedding models).
6. Copy the public URL, e.g. `https://something.up.railway.app`.

### Check the API

In a terminal or browser:

```bash
curl -s https://YOUR-RAILWAY-URL.up.railway.app/health
```

You want JSON that includes:

- `"disclaimer": "Facts-only. No investment advice."`
- `"registry_count": 5`
- a healthy / ready status (not 503)

If `/health` fails, do not share the demo link yet — the index or registry is missing.

---

## Step 3 — Deploy the frontend on Vercel

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. **Add New Project** → import the **same** GitHub repo.
3. Project settings (pick one approach):

   - **Preferred:** set **Root Directory** to `frontend`, framework **Next.js**.
   - **Or** leave Root Directory as `/` — the root `vercel.json` runs `npm install` / `npm run build` with `--prefix frontend`.

4. Under **Environment Variables**, add:

| Variable | Required? | What to put |
| --- | --- | --- |
| `NEXT_PUBLIC_MF_API_URL` | **Yes** | Your Railway URL from Step 2, **no** trailing slash. Example: `https://something.up.railway.app` |

5. Click **Deploy**. When it finishes, copy the Vercel URL (e.g. `https://your-app.vercel.app`).

---

## Step 4 — Connect UI and API (CORS)

The browser only allows the chat site to call the API if Railway knows the Vercel origin.

1. On Railway, set `CORS_ORIGINS` to your exact Vercel URL (and any preview URLs you need), comma-separated.
2. Redeploy the Railway service if you changed the variable after the first deploy.
3. On Vercel, confirm `NEXT_PUBLIC_MF_API_URL` points at Railway (redeploy the frontend if you change it).

Typical order that works well:

1. Deploy Railway with a temporary `CORS_ORIGINS` (or leave it blank only for API smoke tests).
2. Deploy Vercel with `NEXT_PUBLIC_MF_API_URL`.
3. Put the real Vercel URL into Railway `CORS_ORIGINS` and redeploy Railway.

---

## Step 5 — Smoke-test the live demo

1. Open the Vercel URL.
2. Confirm the page shows **Facts-only. No investment advice.** and lists the five schemes.
3. Ask something in scope (e.g. a NAV / expense-ratio style fact about one listed scheme).
4. Ask something that must be refused (e.g. “Should I invest in …?”) and confirm you get a safe refusal — not a stack trace or blank page.
5. If the UI says it cannot reach the API, check:
   - Railway is up and `/health` works
   - `NEXT_PUBLIC_MF_API_URL` has no trailing slash
   - `CORS_ORIGINS` matches the Vercel origin exactly (`https://…`)

---

## Updating fund data later

Ask-time never scrapes Groww live. Fresh data only lands when you refresh artifacts and **redeploy Railway**.

1. Run **Actions → corpus-refresh** (or `make refresh` + force-commit as in Step 1).
2. Trigger a **new Railway deploy** so the new `data/processed` + `data/index` are baked into the image.
3. Frontend on Vercel usually needs no change.

---

## Rollback

- **API:** In Railway, redeploy the previous successful deployment (old image = old index).
- **UI:** In Vercel, promote / redeploy a previous deployment.

---

## Run the same stack on your laptop

Useful before or after cloud deploy.

```bash
# 1) API (from repo root)
# put GROQ_API_KEY in .env (see .env.example)
make serve-api
# or: uvicorn app.api.main:app --host 127.0.0.1 --port 8000

# 2) Next.js UI
cd frontend
cp .env.example .env.local
# NEXT_PUBLIC_MF_API_URL=http://127.0.0.1:8000
npm install
npm run dev
# open http://localhost:3000
```

Optional Streamlit UI (not the production path):

```bash
set MF_API_URL=http://127.0.0.1:8000
streamlit run app/ui/streamlit_app.py
```

---

## Quick checklist

- [ ] Corpus + index committed / available for Docker (`data/processed`, `data/index`)
- [ ] Railway deployed with `GROQ_API_KEY`
- [ ] `curl …/health` looks good (`registry_count`: 5)
- [ ] Vercel deployed with `NEXT_PUBLIC_MF_API_URL` = Railway URL
- [ ] Railway `CORS_ORIGINS` = Vercel URL
- [ ] Live ask + refusal smoke tests pass

---

## Ops notes (short)

- Secrets stay in host env vars — never in the Docker image or git.
- Rate limit is ~30 `/ask` calls per IP per hour (in-memory; fine for one Railway instance).
- Do not advertise the demo until `/health` is green with the strict health check.
- Local Streamlit (`make serve`) still works; the public demo is **Vercel UI + Railway API**.
