# Grid Advisor Console

## Deployment Plan: Google Static Frontend + Cloudflare Tunnel Backend

We will use a low-cost split deployment:

- Frontend: static files under `vue3/`, hosted on Firebase Hosting or Google Cloud Storage.
- Backend: this Windows PC runs Flask with `python run_server.py`.
- Public HTTPS API: Cloudflare Tunnel forwards a public HTTPS hostname to local `http://localhost:5000`.

Traffic path:

```text
User browser
  -> Google/Firebase static frontend
  -> HTTPS API hostname on Cloudflare Tunnel
  -> this PC: Flask backend on localhost:5000
  -> local analyzer, DuckDB, output images
```

## Why This Plan

- Cheap: the expensive calculation stays on this PC.
- No home/office inbound port forwarding is required.
- Cloudflare Tunnel gives an HTTPS endpoint for the local backend.
- The frontend can later move without changing the analyzer code.

## Current Code Preparation

Already prepared in this repo:

- `vue3/index.html` defines `window.GRID_API_BASE` before loading `app.js`.
- `vue3/app.js` sends API requests to `GRID_API_BASE + /api/...`.
- `api_server.py` supports CORS through `ALLOWED_ORIGINS`.
- `run_server.py` starts Flask without the debug reloader.
- `start.bat` starts `run_server.py`.

Local mode:

```html
<script>
  window.GRID_API_BASE = "";
</script>
```

Cloud frontend mode:

```html
<script>
  window.GRID_API_BASE = "https://api.your-domain.example";
</script>
```

## Backend Local Run

From `E:\myApp\Myproject`:

```powershell
python run_server.py
```

Health check:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:5000/api/health
```

## Cloudflare Tunnel Setup

Official docs:

- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/

Recommended production tunnel flow:

```powershell
cloudflared tunnel login
cloudflared tunnel create grid-advisor
cloudflared tunnel route dns grid-advisor api.your-domain.example
```

Create Cloudflare tunnel config, usually at `%USERPROFILE%\.cloudflared\config.yml`:

```yaml
tunnel: grid-advisor
credentials-file: C:\Users\YOUR_USER\.cloudflared\YOUR_TUNNEL_ID.json

ingress:
  - hostname: api.your-domain.example
    service: http://localhost:5000
  - service: http_status:404
```

Run tunnel:

```powershell
cloudflared tunnel run grid-advisor
```

Then test:

```powershell
Invoke-WebRequest -UseBasicParsing https://api.your-domain.example/api/health
```

## CORS Environment Variable

Before starting Flask for the cloud frontend, set `ALLOWED_ORIGINS` to the frontend domain:

```powershell
$env:ALLOWED_ORIGINS="https://your-frontend-domain.web.app,https://your-custom-domain.example,http://localhost:5000"
python run_server.py
```

If CORS is wrong, the browser can load the frontend but API calls will fail.

## Frontend Hosting Option A: Firebase Hosting

Official docs:

- Firebase Hosting: https://firebase.google.com/docs/hosting

Expected Firebase config:

```json
{
  "hosting": {
    "public": "vue3",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"]
  }
}
```

Deploy flow:

```powershell
firebase login
firebase init hosting
firebase deploy
```

Before deploy, set `window.GRID_API_BASE` in `vue3/index.html` to the Cloudflare HTTPS API hostname.

## Frontend Hosting Option B: Google Cloud Storage Static Website

Official docs:

- Cloud Storage static website hosting: https://cloud.google.com/storage/docs/hosting-static-website

This can work, but HTTPS with a custom domain may require additional Google Cloud load balancer setup. Firebase Hosting is simpler for this project.

## Security Notes

- Do not expose plain HTTP to users; use the Cloudflare HTTPS hostname.
- Do not send brokerage passwords through this app.
- Keep `ALLOWED_ORIGINS` narrow; do not use `*` for production.
- Back up `hongdu_analysis.db` regularly.
- Cloudflare can proxy/decrypt HTTPS at its edge because it is the tunnel provider. Ordinary network firewalls should not see request bodies when HTTPS is used.
- Add rate limiting before opening the system to many users.
- Later, replace the current SHA-256 password hash with Werkzeug password hashing or a mature auth system.

## Resume Checklist If Work Is Interrupted

1. Confirm backend starts locally: `python run_server.py`.
2. Confirm local health: `http://localhost:5000/api/health`.
3. Start Cloudflare Tunnel: `cloudflared tunnel run grid-advisor`.
4. Confirm public health: `https://api.your-domain.example/api/health`.
5. Set `window.GRID_API_BASE` in `vue3/index.html` to the Cloudflare HTTPS API hostname.
6. Set backend `ALLOWED_ORIGINS` to the deployed frontend URL.
7. Deploy `vue3/` to Firebase Hosting or Google static hosting.
8. Open the frontend and test register/login.
9. Test grid analysis with one stock before inviting users.

## Approved Development Plans

When the user explicitly approves a technical plan, record it in this README before or alongside implementation. This keeps the project direction recoverable if a terminal session or chat context is interrupted.

### RL + Markov Analysis First Version

Approved direction: do not start by importing the full FinRL-Trading stack. It may be too large for the first version and could slow down integration with the existing analyzer and grid advisor system.

Use a lighter open-source combination first:

- `hmmlearn`: market regime detection with Hidden Markov Models or Markov-style state transitions.
- `gymnasium`: wrap the trading/grid strategy into a standard reinforcement learning environment.
- `stable-baselines3`: train PPO, DQN, SAC, or other RL agents on that environment.

Initial architecture:

```text
Market data / holdings / main-wave indicators
  -> hmmlearn market state detection
  -> Gymnasium TradingEnv
  -> stable-baselines3 agent training
  -> risk-control hard filters
  -> grid parameter suggestion / buy-sell recommendation
  -> automation order module only after simulation validation
```

Rules for the first version:

- RL should produce suggestions first, not direct live orders.
- The risk-control layer must override model output.
- Train on AutoDL 4090 when needed; run inference on the local i5 server.
- Start with a small stock universe and 30-minute or daily bars before expanding.
- Keep FinRL / FinRL-Trading as a later option after the lightweight version works.

## Current Progress Snapshot (2026-05-22)

### Completed

- Local backend starts successfully on this Windows machine.
- Local health check is working:
  - `http://localhost:5000/api/health`
- Cloudflare Zero Trust Free has been activated.
- A `cloudflared` tunnel named `grid-advisor` has been created and connected.
- Domain purchased in Cloudflare:
  - `gridwise-ai.com`
- Public API route has been configured through Cloudflare Tunnel:
  - `api.gridwise-ai.com -> http://localhost:5000`
- Public health check is working:
  - `https://api.gridwise-ai.com/api/health`

### Verified by testing

The following flows were tested successfully against the current local backend:

- user registration
- user login
- `/api/me`
- positions save
- positions load
- `/api/portfolio/analyze`

### Known issue

- `/api/portfolio/timed-analyze` is not fully stable yet.
- In the current smoke test it returned:
  - `RemoteDisconnected('Remote end closed connection without response')`

This means the main system path is working, but the timed analysis path still needs debugging.

### Frontend configuration status

- `vue3/index.html` currently uses:

```html
<script>
  window.GRID_API_BASE = "";
</script>
```

This is correct for local same-origin testing.

Before deploying the frontend to Google / Firebase static hosting, update it to:

```html
<script>
  window.GRID_API_BASE = "https://api.gridwise-ai.com";
</script>
```

### Practical operating note

- In the current local environment, `start.bat` is the reliable way to bring the backend up for browser testing.
- If the local service is not running, the tunnel cannot forward requests to the app.

### Immediate Next Tasks

1. Finish the Google static frontend + Cloudflare Tunnel deployment path end to end.
2. Build the first version of the `hmmlearn + gymnasium + stable-baselines3` training framework.

### Useful Local Network Check

On Windows, scan visible WiFi networks and their security modes with:

```powershell
netsh wlan show networks mode=bssid
```

Use this only for authorized network assessment. Focus on authentication and encryption fields such as `WPA2-Personal`, `WPA3-Personal`, `CCMP`, `Open`, and `WEP`.
