# Share PredictX with a public link

Two options: **permanent free hosting** (recommended) or a **quick tunnel** while your PC is on.

---

## Option A — Permanent link (Render, free)

You get a URL like `https://predictx-xxxx.onrender.com` that works 24/7 without your laptop.

### Steps

1. **Push code to GitHub** (if you haven’t already):
   ```bash
   cd c:\Users\azamo\OneDrive\Desktop\projects\polymarket
   git init
   git add .
   git commit -m "PredictX demo app"
   ```
   Create a repo on [github.com/new](https://github.com/new), then:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/predictx.git
   git push -u origin main
   ```

2. **Deploy on Render**
   - Go to [render.com](https://render.com) → Sign up (free).
   - **New** → **Web Service** → Connect your GitHub repo.
   - Render auto-detects settings from `render.yaml`.
   - Click **Create Web Service** and wait ~2 minutes.

3. **Your public link**  
   Render shows something like:  
   `https://predictx.onrender.com`  
   Share that URL with anyone.

### Custom domain (optional)

If you own a domain (e.g. `predictx.com`):

1. Render dashboard → your service → **Settings** → **Custom Domains**.
2. Add `predictx.com` (or `www.predictx.com`).
3. At your domain registrar, add the DNS records Render shows (usually a CNAME).
4. Render provisions HTTPS automatically.

---

## Option B — Quick tunnel (no signup, PC must stay on)

Get a temporary `https://….trycloudflare.com` link in one command.

### One-time: install Cloudflare Tunnel

Download **cloudflared** for Windows:  
[https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)

Or with winget:
```powershell
winget install --id Cloudflare.cloudflared
```

### Share link

Terminal 1 — start the app:
```powershell
cd c:\Users\azamo\OneDrive\Desktop\projects\polymarket
python main.py
```

Terminal 2 — create public URL:
```powershell
cloudflared tunnel --url http://localhost:8000
```

Copy the `https://….trycloudflare.com` URL from the output and send it.  
The link stops working when you close either terminal.

---

## Notes

- **Demo only** — no real money; data on Render’s free tier may reset after idle sleep or redeploys.
- Free Render apps **spin down after ~15 min idle**; the first visit after that may take 30–60 seconds to wake up.
- For a always-fast demo, use a paid Render plan or Option B while presenting.
