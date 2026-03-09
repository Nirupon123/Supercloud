// ============================================================
// middleware/cache.js
//
// CLOUD/AIOPS ERROR IN THIS FILE:
//
// [ERROR-10] MEMORY LEAK: Unbounded in-memory cache with no eviction.
//   Every unique URL ever requested is stored in a plain JS object.
//   This cache NEVER evicts entries. Over time (hours/days), the Node.js
//   heap grows monotonically until the container is OOMKilled by Kubernetes.
//
//   AIOps detection:
//   - Memory usage metric trends upward continuously
//   - Container restarts with OOMKilled reason
//   - AIOps triggers: pod restart, memory alert, heap dump collection
//
//   Correct implementation: use a proper LRU cache (lru-cache package)
//   with a max entry count and TTL-based expiration.
// ============================================================

const logger = require('../config/logger');

// [ERROR-10] Plain object = no max size, no TTL, no eviction.
// Every GET /api/products?page=1, ?page=2, ?search=foo, etc. adds a new entry.
// In production with many users, this rapidly fills available heap memory.
const memoryCache = {};

const cacheMiddleware = (ttlSeconds = 60) => {
  return (req, res, next) => {
    const key = req.originalUrl;

    if (memoryCache[key]) {
      logger.info(`Cache HIT: ${key} (cache size: ${Object.keys(memoryCache).length} entries)`);
      return res.json(memoryCache[key]);
    }

    // Intercept res.json to store response in cache
    const originalJson = res.json.bind(res);
    res.json = (data) => {
      // [ERROR-10 continued] No size check before writing to cache.
      // A single large payload (e.g. 10,000 products) is stored in full.
      // No cleanup of stale entries — entry stays until process restarts.
      memoryCache[key] = data;
      logger.info(`Cache SET: ${key} (cache size: ${Object.keys(memoryCache).length} entries)`);
      return originalJson(data);
    };

    next();
  };
};

// Expose cache stats route (useful for AIOps observability tooling)
const getCacheStats = () => ({
  entries: Object.keys(memoryCache).length,
  keys: Object.keys(memoryCache),
  // Approximate memory: each object key/value pair is not tracked
  // AIOps must rely on process.memoryUsage() to detect the leak
});

module.exports = { cacheMiddleware, getCacheStats };
