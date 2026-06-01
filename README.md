# PredictX — Prediction Markets

A Polymarket-style web app where you can **create markets on any event** and **bet Yes or No** with dynamic odds powered by a constant-product AMM.

## Features

- Browse and search prediction markets
- Create custom markets (any question + resolution criteria)
- Buy Yes/No shares — prices update with supply and demand
- Portfolio with positions and P&L tracking
- Demo wallet ($1,000 starting balance)
- Resolve markets and pay out winners (demo admin controls)

## Quick start

```bash
cd polymarket
pip install -r requirements.txt
python main.py
```

Open **http://localhost:8000** in your browser.

## Render environment variables

Render does **not** load `.env` from the repo. Add variables in the dashboard:

**[RENDER_ENV.md](RENDER_ENV.md)** — step-by-step for `SECRET_KEY`, `ENV`, `BASE_URL`, and Google OAuth.

## Share with others (public link)

See **[DEPLOY.md](DEPLOY.md)** for full instructions.

**Quick share (while your PC is on):**
```powershell
.\share.ps1
```
Or run `python main.py` in one terminal and `cloudflared tunnel --url http://localhost:8000` in another — copy the `https://….trycloudflare.com` URL.

**Permanent link (free):** Deploy to [Render](https://render.com) using `render.yaml` → get `https://your-app.onrender.com`. Optional custom domain in Render settings.

## How it works

- Each market starts with equal Yes/No liquidity (50/50 implied probability).
- When you buy Yes shares, you add USDC to the pool; the Yes price rises (like Polymarket).
- Shares pay **$1 each** if your side wins when the market is resolved.
- Your balance and positions persist in a local SQLite database (`predict.db`).

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/markets` | List markets (`?status=open`, `?q=search`) |
| POST | `/api/markets` | Create market |
| GET | `/api/markets/{id}` | Market detail + recent trades |
| POST | `/api/markets/{id}/bet` | Place bet `{ user_id, side, amount }` |
| POST | `/api/markets/{id}/resolve` | Resolve `{ resolution: "yes" \| "no" }` |
| GET | `/api/users/{id}` | User balance + positions |

## Stack

- **Backend:** Python, FastAPI, SQLite
- **Frontend:** Vanilla JS, CSS (Polymarket-inspired dark UI)

This is a **demo** app — no real money or blockchain. Install [Node.js](https://nodejs.org/) separately if you want to migrate to a Next.js production build later.
