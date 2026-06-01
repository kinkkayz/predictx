# Persistent data on Render

Redeploys used to wipe data because the app stored everything in a **local SQLite file**.  
Now it uses **PostgreSQL** — users, balances, and markets survive redeploys.

## If you already have a live site (do this once)

### 1. Create a database

1. [dashboard.render.com](https://dashboard.render.com) → **New +** → **PostgreSQL**
2. Name: `predictx-db` → **Free** → **Create Database**
3. Wait until status is **Available**

### 2. Connect it to your web service

1. Open the **predictx** web service (not the database)
2. **Environment** → **Add Environment Variable**
3. Key: `DATABASE_URL`
4. Value: open **predictx-db** → copy **Internal Database URL** (starts with `postgresql://`)
5. **Save, rebuild, and deploy**

### 3. Optional admin email

| Key | Value |
|-----|--------|
| `ADMIN_EMAIL` | Your sign-up email (only you can resolve markets) |

### 4. Google sign-in (optional)

On the **predictx** web service, add:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

Step-by-step: **[GOOGLE_SETUP.md](GOOGLE_SETUP.md)**

---

## Local development

No `DATABASE_URL` → uses `predict.db` on your PC (same as before).

---

## New deploys from Blueprint

`render.yaml` includes Postgres automatically. Use **New → Blueprint** and connect the repo.

---

## Note

Render **free Postgres** may expire after 90 days of inactivity (Render policy). For a long-lived demo, check your Render dashboard or upgrade.
