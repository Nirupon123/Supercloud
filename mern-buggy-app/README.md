# MERN Buggy App — AIOps Self-Healing Test Project

A MERN stack e-commerce app with **12 deliberate cloud/infrastructure-level errors** for testing AIOps self-healing platforms. The application code logic is functionally correct — all errors are **operational and deployment-level**, the kind that surface in cloud environments and are remediated by AIOps tooling.

## Project Structure

```
mern-buggy-app/
├── backend/
│   ├── config/
│   │   ├── db.js          ← ERROR-5, 6, 7: pool, retry, timeout
│   │   └── logger.js      ← ERROR-8, 9: file logging, no rotation
│   ├── controllers/
│   │   ├── authController.js
│   │   └── productController.js  ← ERROR-12: CPU spike
│   ├── middleware/
│   │   ├── auth.js
│   │   └── cache.js       ← ERROR-10: memory leak
│   ├── models/
│   │   ├── User.js
│   │   └── Product.js
│   ├── routes/
│   │   ├── auth.js
│   │   ├── health.js      ← ERROR-11: misleading health check
│   │   └── products.js
│   ├── .env               ← ERROR-1, config drift: missing PORT, NODE_ENV
│   ├── package.json
│   └── server.js          ← ERROR-1, 2, 3, 4: crash loop, no SIGTERM, verbose errors
└── frontend/
    └── src/
        ├── components/    ← All functionally correct
        ├── services/
        │   └── api.js     ← ERROR-13, 14: no retry, no timeout
        └── App.js
```

## Quick Start

### Backend
```bash
cd backend
# Add PORT=5000 to .env first, or the server will crash (intentional — ERROR-1)
npm run dev
```

### Frontend
```bash
cd frontend
npm start
```

---

## 🛠 Cloud/Infrastructure Errors Catalog

| # | File | Error | AIOps Detection & Remediation |
|---|------|-------|-------------------------------|
| **ERROR-1** | `server.js` | **CrashLoopBackOff**: `PORT` env var required with no fallback. Missing in container manifest → `process.exit(1)` → k8s restart loop | Detects restart loop, alerts on-call, triggers manifest remediation job |
| **ERROR-2** | `server.js` | **No Graceful SIGTERM**: SIGTERM not handled. Rolling deploy drops all in-flight requests instantly | Detects 5xx spike correlated with deploy events, triggers canary rollback |
| **ERROR-3** | `server.js` | **Verbose Errors in Production**: Full stack traces sent to API clients. `NODE_ENV` not set → Express dev mode | SIEM/security scanner detects sensitive data in response bodies |
| **ERROR-4** | `server.js` | **No Request Timeout**: `server.timeout` not set (default: infinite). Stalled DB queries hold HTTP connections forever → file descriptor exhaustion | Detects open connection count trending up, triggers request queue alert |
| **ERROR-5** | `config/db.js` | **Connection Pool Exhaustion**: `maxPoolSize: 1` serializes all DB ops. Any concurrent load creates indefinitely growing queue | Detects p99 DB wait time spike, remediates by adjusting pool config |
| **ERROR-6** | `config/db.js` | **No DB Retry Logic**: Single connect attempt. Transient DNS/network blip during pod startup = permanent startup failure | Detects startup failure pattern, triggers retry remediation with backoff |
| **ERROR-7** | `config/db.js` | **Aggressive Timeout (100ms)**: `serverSelectionTimeoutMS: 100`. Cross-AZ cloud DB latency easily exceeds this → constant failures | Detects connection timeout rate spike, adjusts timeout via config push |
| **ERROR-8** | `config/logger.js` | **Logging to File (not stdout)**: Cloud log agents (Fluentd, CloudWatch) collect from stdout/stderr only. File-based logs are invisible to all cloud logging infra | Log gap detection: no logs visible in aggregator despite active traffic |
| **ERROR-9** | `config/logger.js` | **No Log Rotation**: Append-only log file with no size cap. High-traffic pod fills container disk → ENOSPC → app crash | Disk usage metric > threshold triggers cleanup job or disk resize |
| **ERROR-10** | `middleware/cache.js` | **Memory Leak**: Plain JS object cache with no TTL, no eviction, no max size. Every unique URL adds a permanent entry → heap grows until OOMKilled | Memory usage trends upward continuously; AIOps restarts pod before OOM, triggers heap dump |
| **ERROR-11** | `routes/health.js` | **Misleading Health Check**: `/health` always returns `200 OK` even when MongoDB is disconnected. Kubernetes liveness probe never detects sick pod | AIOps detects rising 5xx rate from pod while health check passes — "anomalous healthy pod" pattern triggers forced eviction |
| **ERROR-12** | `controllers/productController.js` | **CPU Spike / Event Loop Blocking**: Synchronous `JSON.parse/JSON.stringify` loop (5,000 iterations) in `GET /products/:id` hot path. Blocks Node.js event loop → all concurrent requests stall | CPU p99 breach correlated with request latency spike triggers horizontal scale-out |
| **ERROR-13** | `frontend/src/services/api.js` | **No HTTP Retry**: Transient 503/network errors immediately surface as user-visible failures. No backoff retry | High rate of short-lived client errors correlated with infra events triggers retry policy enforcement |
| **ERROR-14** | `frontend/src/services/api.js` | **No Request Timeout (Client)**: No `axios` timeout set. If backend is stalled (CPU blocked, event loop stalled), frontend hangs indefinitely | P99 frontend request duration anomaly correlated with backend CPU spike |

---

## Error Categories

| Category | Errors | Count |
|----------|--------|-------|
| Process Lifecycle / Crash Loop | ERROR-1, ERROR-2 | 2 |
| Missing Config / Env Drift | ERROR-1, ERROR-3 | 2 |
| Resource Exhaustion | ERROR-4, ERROR-5, ERROR-10 | 3 |
| Startup Resilience | ERROR-6, ERROR-7 | 2 |
| Observability Gap | ERROR-8, ERROR-9 | 2 |
| Health Check Integrity | ERROR-11 | 1 |
| Compute / CPU | ERROR-12 | 1 |
| Client Resilience | ERROR-13, ERROR-14 | 2 |

---

## How to Trigger Each Error

| Error | How to Trigger |
|-------|----------------|
| ERROR-1 (crash loop) | Leave `.env` without `PORT=5000` and run `node server.js` |
| ERROR-2 (dropped requests) | Start server, open a long-running request, then kill with Ctrl+C — request drops immediately |
| ERROR-4 (connection exhaustion) | Use a DB query with artificial delay; watch open connection count rise |
| ERROR-5 (pool exhaustion) | Send 5+ concurrent requests to any endpoint — all but 1 queue up |
| ERROR-8 (no cloud logs) | Run server, make requests, then check terminal — no output. Check `./logs/app.log` instead |
| ERROR-10 (memory leak) | Send `GET /api/products` with many unique query strings, monitor `process.memoryUsage()` |
| ERROR-11 (misleading health) | Stop MongoDB, then `curl http://localhost:5000/health` — still returns `200 OK` |
| ERROR-12 (CPU spike) | `GET /api/products/:id` — observe CPU spike in Task Manager |
