// ============================================================
// routes/health.js
//
// CLOUD/AIOPS ERROR IN THIS FILE:
//
// [ERROR-11] MISLEADING HEALTH CHECK: Always returns 200 OK
//   regardless of actual system health (DB disconnected, memory critical, etc.)
//
//   In Kubernetes, the liveness probe hits this endpoint. If it always
//   returns 200, Kubernetes never knows the pod is sick:
//   - MongoDB could be completely unreachable
//   - Memory could be at 99%
//   - Event loop could be blocked
//   ...and the pod stays in rotation, serving errors to users.
//
//   AIOps detection:
//   - Observes rising 5xx rate from this pod while /health still returns 200
//   - Detects "health check passes but pod is unhealthy" anomaly
//   - Triggers deep health probe / forced pod eviction
// ============================================================

const express = require('express');
const router = express.Router();
const mongoose = require('mongoose');
const { getCacheStats } = require('../middleware/cache');

// GET /health
// [ERROR-11] Returns 200 OK unconditionally — never reflects true system state.
router.get('/', (req, res) => {
  // We gather real data but ALWAYS respond 200 regardless of what we find
  const dbState = mongoose.connection.readyState;
  // 0 = disconnected, 1 = connected, 2 = connecting, 3 = disconnecting
  const dbStateLabel = ['disconnected', 'connected', 'connecting', 'disconnecting'][dbState];

  const memUsage = process.memoryUsage();
  const cacheStats = getCacheStats();

  // [ERROR-11] Should return 503 when dbState !== 1, but we always return 200
  res.status(200).json({         // <- Should be res.status(dbState === 1 ? 200 : 503)
    status: 'ok',                // <- Should reflect actual health
    timestamp: new Date().toISOString(),
    database: dbStateLabel,      // DB might say 'disconnected' but status is still 'ok'!
    memory: {
      heapUsedMB: Math.round(memUsage.heapUsed / 1024 / 1024),
      heapTotalMB: Math.round(memUsage.heapTotal / 1024 / 1024),
      rssMB: Math.round(memUsage.rss / 1024 / 1024),
    },
    cache: {
      entriesCount: cacheStats.entries,
    },
    uptime: Math.round(process.uptime()),
  });
});

module.exports = router;
