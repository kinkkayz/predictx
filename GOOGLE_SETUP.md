# Google Sign-In Setup

## 1. Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or pick an existing one)
3. **APIs & Services** → **OAuth consent screen**
   - User type: **External**
   - Add your email as a test user (while app is in "Testing")
4. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
   - Application type: **Web application**
   - **Authorized redirect URIs** — add both:
     - `https://predictx-dwu1.onrender.com/api/auth/google/callback`
     - `http://localhost:8000/api/auth/google/callback` (for local dev)

Copy the **Client ID** and **Client secret**.

## 2. Render environment variables

In [Render Dashboard](https://dashboard.render.com) → your **predictx** service → **Environment**:

| Key | Value |
|-----|--------|
| `SECRET_KEY` | Long random string (e.g. run `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ENV` | `production` |
| `BASE_URL` | `https://predictx-dwu1.onrender.com` |
| `GOOGLE_CLIENT_ID` | From Google Console |
| `GOOGLE_CLIENT_SECRET` | From Google Console |

Save → Render redeploys automatically.

## 3. Verify

Open your site → **Sign up** → **Continue with Google** should appear and work after login.

Without Google env vars, email/password signup still works.
