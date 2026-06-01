# Add environment variables on Render

Render **does not** use a `.env` file from your repo. You add variables in the **Render website**.

## Step-by-step

1. Open [dashboard.render.com](https://dashboard.render.com)
2. Click your service (**predictx** or **predictx-dwu1**)
3. In the left sidebar, click **Environment**
4. Click **+ Add Environment Variable**
5. Add each row below (one at a time)
6. Click **Save Changes** at the bottom  
   → Render redeploys automatically (~2–5 min)

## Variables to add

### Required (do these first)

| Key | Value |
|-----|--------|
| `SECRET_KEY` | Paste a long random string — generate one: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ENV` | `production` |
| `BASE_URL` | `https://predictx-dwu1.onrender.com` |

Use **your exact** Render URL if it’s different (top of the service page, e.g. `https://predictx-xxxx.onrender.com`).

### Optional (only for Google sign-in)

| Key | Value |
|-----|--------|
| `GOOGLE_CLIENT_ID` | From [Google Cloud Console](https://console.cloud.google.com/) → Credentials |
| `GOOGLE_CLIENT_SECRET` | Same place as Client ID |

See [GOOGLE_SETUP.md](GOOGLE_SETUP.md) for Google OAuth setup.

**Without Google variables:** email/password signup and login still work. The Google button stays hidden.

## Checklist

- [ ] `SECRET_KEY` set (keeps users logged in across redeploys)
- [ ] `ENV` = `production`
- [ ] `BASE_URL` = your `https://….onrender.com` URL (no trailing slash)
- [ ] Saved and deploy finished (green **Live**)
- [ ] Google vars (only if you want “Continue with Google”)

## Troubleshooting

**“I don’t see Environment”**  
You must open the **Web Service**, not the project overview. Click the service name first.

**“render.yaml has them but they’re missing”**  
If you created the service with **New Web Service** (not Blueprint), `render.yaml` is ignored. Add variables manually as above.

**Google login fails**  
`BASE_URL` must match your live URL exactly. Redirect URI in Google must be:  
`https://YOUR-URL.onrender.com/api/auth/google/callback`
