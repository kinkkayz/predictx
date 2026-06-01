# Google Sign-In — setup checklist

The button appears automatically after you add **two** variables on Render. No code changes needed.

---

## Step 1 — Google Cloud (5 minutes)

1. Open **[console.cloud.google.com](https://console.cloud.google.com/)** and sign in.

2. **Select a project** (top bar) → **New Project** → name it `PredictX` → **Create**.

3. **OAuth consent screen** (left menu → APIs & Services):
   - Click **Get started** or **Configure**
   - User type: **External** → **Create**
   - App name: `PredictX`
   - User support email: your email
   - Developer contact: your email
   - **Save and continue** through Scopes (defaults are fine)
   - **Test users** → **Add users** → add **your Gmail** (required while app is in "Testing")
   - **Save**

4. **Credentials** → **Create credentials** → **OAuth client ID**:
   - Application type: **Web application**
   - Name: `PredictX Web`
   - **Authorized redirect URIs** → **Add URI**:
     ```
     https://predictx-dwu1.onrender.com/api/auth/google/callback
     ```
     (If your Render URL is different, use that instead — no trailing slash.)

5. Click **Create**. Copy:
   - **Client ID** → looks like `123456789-xxxx.apps.googleusercontent.com`
   - **Client secret** → looks like `GOCSPX-xxxxxxxx`

---

## Step 2 — Render (1 minute)

1. [dashboard.render.com](https://dashboard.render.com) → open **predictx** (web service)
2. **Environment** → **Add Environment Variable**

| Key | Paste this |
|-----|------------|
| `GOOGLE_CLIENT_ID` | Client ID (ends in `.apps.googleusercontent.com`) |
| `GOOGLE_CLIENT_SECRET` | Client secret (starts with `GOCSPX-`) |

3. **Save, rebuild, and deploy** → wait until **Live**

**Do not** put the Google secret in `SECRET_KEY`. Only use the two keys above.

---

## Step 3 — Test

1. Open [https://predictx-dwu1.onrender.com](https://predictx-dwu1.onrender.com)
2. You should see **Continue with Google** under the login form
3. Click it → pick your Google account → you land in the app with $1,000 demo balance

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No Google button | `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` missing on Render — redeploy after adding |
| `redirect_uri_mismatch` | Redirect URI in Google must **exactly** match `https://YOUR-SITE.onrender.com/api/auth/google/callback` |
| `access_denied` | Add your Gmail under OAuth consent screen → **Test users** |
| Google works but email login fails for same address | Use Google for that email, or use a different email for password signup |

---

## Optional: local testing

Add to a `.env` file (not committed):

```
GOOGLE_CLIENT_ID=your-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
```

Also add redirect URI in Google:

```
http://localhost:8000/api/auth/google/callback
```

Run `python main.py` and open http://localhost:8000
