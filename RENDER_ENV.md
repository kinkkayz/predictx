# Render setup (simple)

**You do not need to add any environment variables.**

Render automatically provides your site URL. Login sessions are configured in code.

## If you already added variables

1. [dashboard.render.com](https://dashboard.render.com) → **predictx** → **Environment**
2. **Delete every variable** (especially if `SECRET_KEY` contains `GOCSPX-` — that is a Google secret, not the right field)
3. Click **Save, rebuild, and deploy**
4. Wait until **Live**, then open your site and **Sign up** with email + password

## Optional: Google sign-in later

Only if you want it — add exactly these two variables (nothing else):

- `GOOGLE_CLIENT_ID` — from Google Cloud Console
- `GOOGLE_CLIENT_SECRET` — the `GOCSPX-...` value

See [GOOGLE_SETUP.md](GOOGLE_SETUP.md).
