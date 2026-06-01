# Google Sign-In Setup

**Prerequisite:** Add `SECRET_KEY`, `ENV`, and `BASE_URL` on Render first — see [RENDER_ENV.md](RENDER_ENV.md).

## 1. Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or pick an existing one)
3. **APIs & Services** → **OAuth consent screen**
   - User type: **External**
   - Add your email as a **test user** (while app is in "Testing")
4. **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
   - Application type: **Web application**
   - **Authorized redirect URIs** — add:
     - `https://predictx-dwu1.onrender.com/api/auth/google/callback`
     - `http://localhost:8000/api/auth/google/callback` (optional, for local dev)

Copy the **Client ID** and **Client secret**.

## 2. Add to Render

[dashboard.render.com](https://dashboard.render.com) → your service → **Environment** → **Add Environment Variable**:

| Key | Value |
|-----|--------|
| `GOOGLE_CLIENT_ID` | Paste Client ID |
| `GOOGLE_CLIENT_SECRET` | Paste Client secret |

**Save Changes** and wait for redeploy.

## 3. Verify

Open your site → you should see **Continue with Google** on the login screen.
