# Render — Hosting Reference

**Selected:** 2026-04-06  
**Current plan:** Free (demo only)  
**Recommended upgrade:** Starter + 5 GB persistent disk ($8.25/month)  
**Primary use:** FastAPI web service — 5-step puzzle wizard, SQLite job tracking, Replicate API calls

> **Consultant note:** The free tier is viable for demos but is a silent data-loss risk for real orders — any deploy or infrastructure restart wipes `orders/` and the SQLite jobs database entirely. The path to production is straightforward: upgrade to the Starter plan ($7/month) and attach a 5 GB persistent disk ($1.25/month). Move `orders/` and `jobs.db` under the mount path (`/data`). Four small code changes and one yaml tweak. At 5–20 orders/month, $8.25/month is the correct hosting cost.

---

## Service Tiers

All prices are per service per month, billed by the second (prorated). The app is IO-bound (waiting on Replicate), not CPU-bound, so RAM and CPU headroom matter more than raw speed.

| Plan | Price/month | RAM | CPU | Sleeps? | SSH? | Persistent Disk? |
|------|-------------|-----|-----|---------|------|------------------|
| **Free** | $0 | 512 MB | 0.1 vCPU | Yes — 15 min idle | No | No |
| **Starter** | $7 | 512 MB | 0.5 vCPU | No | Yes | Yes |
| **Standard** | $25 | 2 GB | 1 vCPU | No | Yes | Yes |
| **Pro** | $85 | 4 GB | 2 vCPU | No | Yes | Yes |
| **Pro Plus** | $175 | 8 GB | 4 vCPU | No | Yes | Yes |

CPU figures are fractional vCPUs. Autoscaling requires a **Professional workspace** ($19/user/month on top of instance cost) — not needed at our volume.

### Free tier constraints

- Spins down after **15 minutes of no inbound traffic**. Cold start takes ~1 minute — real customers see a loading spinner.
- **750 instance-hours per calendar month** shared across all free services.
- **500 build pipeline minutes per month** (shared). Each deploy uses minutes; exceeding this stops builds until next billing cycle.
- **100 GB outbound bandwidth per month**.
- No persistent disk, no SSH, no scaling, no private networking.
- Render may restart free services at any time and can suspend unusually high-traffic services without warning.

---

## Ephemeral Filesystem

By default all Render services use an ephemeral filesystem. There is no warning when data is lost — it is silent.

| Event | Filesystem wiped? |
|-------|-------------------|
| **Deploy** (code push, env var change, manual redeploy) | **Yes — everything outside a mounted disk path is destroyed** |
| **Restart** (OOM kill, crash, Render infrastructure restart) | **Yes — same wipe** |
| **Sleep / spin-down** (free tier idle) | **Yes — same wipe on wake** |
| Normal request handling (service running) | No — stable |

**For this app:** `orders/` output files, `jobs.db` (SQLite), and any cached data are all wiped on every deploy or restart unless stored on a persistent disk.

---

## Persistent Disk

A persistent disk survives deploys and restarts. It is the only way to keep runtime-written files on Render without using an external storage service.

### Availability and cost

- **Not available on the Free tier.** Requires Starter ($7/month) or above.
- **$0.25 per GB per month**, billed by the second.
- 5 GB = $1.25/month. Default in `render.yaml` is 10 GB ($2.50/month) — overkill at launch.
- Disk size can only **increase**, never decrease (contact Render support to resize down).

### How it works

- Specify an absolute **mount path** (e.g. `/data`). Only changes under that path survive a deploy or restart.
- Everything outside the mount path remains ephemeral.
- Encrypted at rest. Automatic daily snapshots kept for 7+ days.

### Key gotchas

1. **Disables zero-downtime deploys.** Render must stop the old instance before starting the new one (prevents two instances writing simultaneously). Brief downtime on every deploy.
2. **Single instance only.** Cannot scale to multiple instances with a disk attached.
3. **Inaccessible during build phase** — only the running service process can read/write it.
4. **Cannot be added to cron jobs.**

### What to store on the disk

| Store here | Don't store here |
|------------|------------------|
| `orders/` output directory | Python dependencies (belong in build) |
| `jobs.db` SQLite database | Static assets (serve from repo or CDN) |
| Any other runtime-written files | |

---

## Environment Variables

### How to set them

**Dashboard:** Service → Environment tab → Add Environment Variable. Bulk-import from a `.env` file supported.  
**render.yaml:** Declare in `envVars` array — use `sync: false` for secrets (keeps them out of git, prompts manual entry on first deploy).

When saving in the dashboard, choose:
- *Save and deploy* — redeploys with new vars using existing build artifact (fast)
- *Save, rebuild, and deploy* — full new build (use when deps change)
- *Save only* — defers until next manual deploy

### Limits

- No documented cap on number of variables.
- **Secret files:** combined size ≤ 1 MB per service.
- No free vs paid difference — env vars work identically on all tiers.

### Important built-in variable

Render injects `PORT` (default `10000`). The app **must** bind to `0.0.0.0:$PORT` — a hardcoded port (e.g. `8000`) will fail.

### Environment Groups

Create a named group of variables in the dashboard and link it to multiple services. Useful for sharing `REPLICATE_API_TOKEN` and `ANTHROPIC_API_KEY` across services. Service-level variables override group variables when the same key exists in both.

---

## Auto-Deploy from GitHub

1. Connect your GitHub repo during service creation or via the Settings tab.
2. Specify the **branch** to watch (e.g. `main`).
3. Every push or merge to that branch triggers an automatic rebuild and redeploy.
4. Optional: `autoDeployTrigger: checksPass` waits for GitHub Actions CI to pass before deploying.
5. Optional: `autoDeployTrigger: off` for fully manual-only deploys.

### Build pipeline

```
buildCommand runs   →   startCommand runs
(pip install, etc.)     (uvicorn, gunicorn, etc.)
```

- `preDeployCommand` runs after build, before start — good for DB migrations.
- Build timeout: 120 minutes.
- Build minutes count against your monthly allocation.

### Zero-downtime deploys

Available on paid tiers **without** a persistent disk: Render spins up the new instance, waits for the health check to pass, then switches traffic. Old instance gets a 30-second graceful shutdown window (configurable up to 300 seconds). **Disabled if a disk is attached** — we accept brief downtime per deploy in exchange for persistent storage.

---

## render.yaml Reference

The `render.yaml` file at the root of your repo defines your infrastructure (Render calls this "Blueprints"). Render reads it on first connect and on each deploy.

### Full field reference for web services

```yaml
services:
  - type: web                          # web | private | worker | cron
    name: my-service                   # Unique name in your workspace
    runtime: python                    # node | python | elixir | go | ruby | rust | docker
    plan: starter                      # free | starter | standard | pro | pro plus | pro max | pro ultra
    region: oregon                     # oregon (default) | ohio | virginia | frankfurt | singapore

    # Source
    repo: https://github.com/org/repo  # Defaults to the repo containing render.yaml
    branch: main

    # Commands
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn web.app:app --host 0.0.0.0 --port $PORT
    preDeployCommand: python manage.py migrate   # Runs after build, before start

    # Deploy behaviour
    autoDeployTrigger: commit          # commit | checksPass | off
    healthCheckPath: /health           # Endpoint Render polls to confirm healthy start
    maxShutdownDelaySeconds: 30        # 1–300; grace period before SIGKILL

    # Custom domains
    domains:
      - myapp.example.com

    # Persistent disk (paid plans only)
    disk:
      name: app-data                   # Logical name
      mountPath: /data                 # Absolute path — only this path persists
      sizeGB: 5                        # Default 10; can only increase, never decrease

    # Scaling (manual — all plans; autoscaling — Professional workspace only)
    numInstances: 1

    # Environment variables
    envVars:
      - key: PYTHON_ENV
        value: production
      - key: SECRET_KEY
        generateValue: true            # Render generates random value on first deploy
      - key: API_TOKEN
        sync: false                    # Value entered manually in dashboard; never in yaml
      - fromGroup: shared-secrets      # Pull all vars from a named environment group
```

### Minimal config for this project

```yaml
services:
  - type: web
    name: ai-puzzle-mvp
    runtime: python
    plan: starter
    branch: main

    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn web.app:app --host 0.0.0.0 --port $PORT --workers 1

    healthCheckPath: /health

    disk:
      name: orders-data
      mountPath: /data
      sizeGB: 5

    envVars:
      - key: REPLICATE_API_TOKEN
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: PYTHON_VERSION
        value: "3.11.6"
      - key: DATABASE_PATH
        value: /data/jobs.db
```

---

## Production-Ready Configuration

### Recommended setup

| Component | Spec | Monthly cost |
|-----------|------|-------------|
| Web service | Starter — 512 MB RAM, 0.5 vCPU | $7.00 |
| Persistent disk | 5 GB — stores `orders/` + SQLite DB | $1.25 |
| **Total** | | **$8.25** |

This is sufficient for 5–20 orders/month because:
- Jobs are IO-bound (waiting on Replicate API), not CPU-bound — 0.5 vCPU is fine
- 512 MB RAM covers FastAPI + Pillow + pipeline code (~150 MB peak)
- 5 GB disk holds ~250 orders at 20 MB each before cleanup is needed
- No sleep means the web UI is always responsive for customers

**Upgrade to Standard ($25/month) if:** OOM kills appear in Render metrics, you add concurrency (multiple simultaneous orders), or build times become a bottleneck.

### Code changes required before upgrading

The current codebase writes to paths relative to the project root — these will be in the ephemeral layer even on a paid plan unless the code is updated.

| Change | File | Detail |
|--------|------|--------|
| Move `orders/` output to `/data/orders/` | `web/jobs.py`, `src/pipeline_steps.py` | Update any hardcoded `orders/` path references |
| Move SQLite DB to `/data/jobs.db` | `web/jobs.py` | Read `DATABASE_PATH` env var for DB path |
| Add `/health` endpoint | `web/app.py` | `return {"status": "ok"}` — used by Render's health check |
| Bind to `$PORT` | `render.yaml` start command | `--port $PORT` not `--port 8000` |

---

## Cost Recommendation

| Scenario | Plan + disk | Monthly cost | Notes |
|----------|-------------|-------------|-------|
| Demo / testing only | Free | $0 | Ephemeral filesystem, sleeps — not for real orders |
| **Live launch** | Starter + 5 GB disk | **~$8.25** | **Recommended. Always on, survives deploys.** |
| Higher volume or concurrency | Standard + 5 GB disk | ~$26.25 | Upgrade if hitting RAM limits or running parallel jobs |

**Bottom line:** Switch from Free to Starter + 5 GB disk before taking any real customer orders. The risk is not theoretical — a routine deploy or Render infrastructure restart silently destroys `orders/` and `jobs.db` on the free tier.

---

## Gotchas Summary

| Topic | Gotcha |
|-------|--------|
| Ephemeral filesystem | Deploy AND restart wipe everything outside the mounted disk path. No warning — silent data loss. |
| Free tier sleep | 15-min idle → ~1-min cold start. Real customers see a Render loading page. |
| Disk + zero-downtime | Mutually exclusive. A disk attachment means brief downtime on every deploy. |
| Disk size | Can only grow, not shrink. Start small (5 GB). |
| Disk + scaling | Single instance only — cannot run 2+ instances with a disk attached. |
| Autoscaling | Requires Professional workspace ($19/user/month) on top of instance cost — overkill for our volume. |
| Build minutes | 500 free minutes/month on Hobby plan. Exceeded = no deploys until next billing cycle. |
| `PORT` variable | Must bind to `0.0.0.0:$PORT`. Hardcoded port 8000 will fail silently. |
| `sync: false` | Use for secrets in render.yaml — keeps them out of git, requires manual entry in dashboard on first deploy. |
| Disk inaccessible during build | Build phase cannot read/write the disk — only the running process can. |

---

## Decision Log

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| Hosting platform | Render | Simple GitHub-push deploys, Python-native, generous free tier for demos | 2026-04-06 |
| Current plan | Free | Pre-launch demo only — no real customer orders yet | 2026-04-06 |
| Upgrade target | Starter + 5 GB disk ($8.25/month) | Cheapest plan with persistent disk; free tier ephemeral filesystem is a data-loss risk for real orders | 2026-04-06 |
| Disk mount path | `/data` | Convention; `orders/` → `/data/orders/`, `jobs.db` → `/data/jobs.db` | 2026-04-06 |
| Workers | 1 (`--workers 1`) | Single instance with persistent disk — multiple workers would not help and can conflict on the DB | 2026-04-06 |
| Region | Oregon (default) | No UK region available; Oregon is fine for a UK business running AI inference remotely | 2026-04-06 |

---

*Sources: render.com/pricing, render.com/docs/free, render.com/docs/disks, render.com/docs/web-services, render.com/docs/blueprint-spec, render.com/docs/configure-environment-variables, render.com/docs/deploys, render.com/docs/faq — fetched April 2026.*
