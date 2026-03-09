// ============================================================
// server.js
//
// CLOUD/AIOPS ERRORS IN THIS FILE:
//
// [ERROR-1] CRASH LOOP: PORT is required from env with no fallback.
//   If the container/pod doesn't inject PORT, process exits immediately.
//   Kubernetes will enter CrashLoopBackOff. AIOps detects restart loop.
//
// [ERROR-2] NO GRACEFUL SHUTDOWN: SIGTERM is not handled.
//   When Kubernetes kills this pod during rolling deploy, all in-flight
//   HTTP requests are dropped instantly. AIOps detects 5xx spike on deploy.
//
// [ERROR-3] VERBOSE ERRORS IN ALL ENVIRONMENTS: Full error stack traces
//   sent to clients regardless of NODE_ENV. In production this leaks
//   internal structure. AIOps / SIEM detects sensitive data in responses.
//
// [ERROR-4] NO REQUEST TIMEOUT: No server-level or route-level timeout.
//   A slow MongoDB query holds an HTTP connection open forever, exhausting
//   the file descriptor limit. AIOps detects open connection count spike.
// ============================================================

const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const connectDB = require('./config/db');
const logger = require('./config/logger');
const morgan = require('morgan');

dotenv.config();

const app = express();

// [ERROR-1] CRASH LOOP — No fallback for PORT.
// In a properly configured container PORT is injected via env.
// If the env var is missing (misconfigured deployment manifest),
// the server will fail to bind and Kubernetes enters CrashLoopBackOff.
const PORT = process.env.PORT; // Should be: process.env.PORT || 5000
if (!PORT) {
  logger.error('FATAL: PORT environment variable is not set. Exiting.');
  process.exit(1); // <- Kubernetes sees exit code 1, restarts pod immediately
}

app.use(cors("*"));
app.use(express.json());
app.use(morgan('combined', { stream: logger.stream }));

// Routes
app.use('/api/auth', require('./routes/auth'));
app.use('/api/products', require('./routes/products'));
app.use('/health', require('./routes/health'));

app.get('/', (req, res) => {
  res.json({ message: 'MERN App API Running' });
});

// --- CLOUD-NATIVE ERROR SIMULATIONS FOR AIOPS ---

// [ERROR-5] MEMORY LEAK: Gradually consumes heap memory.
// Cloud orchestrators (K8s) will kill the pod once it hits the cgroup limit (OOM).
// AIOps detects the "Sawtooth" memory pattern.
let leakArray = [];
app.get('/api/leak', (req, res) => {
  logger.warn('AIOps-TEST: Triggering intentional memory leak...');
  for (let i = 0; i < 10000; i++) {
    leakArray.push({ timestamp: Date.now(), data: new Array(1000).fill('leak-metadata') });
  }
  const memory = process.memoryUsage();
  res.json({
    message: "Memory leak in progress.",
    heapUsed: `${(memory.heapUsed / 1024 / 1024).toFixed(2)} MB`,
    leakCount: leakArray.length
  });
});

// [ERROR-6] LATENCY SPIKE: Artificial delay.
// Simulates network congestion, noisy neighbor, or cold-start issues.
// AIOps detects "P99 latency breach" and triggers auto-scaling or traffic shifting.
app.get('/api/slow', (req, res) => {
  const delay = Math.floor(Math.random() * 5000) + 2000; // 2-7 seconds
  logger.warn(`AIOps-TEST: Simulating latent response: ${delay}ms`);
  setTimeout(() => {
    res.json({
      message: `Response delayed by ${delay}ms`,
      delay,
      node: process.env.HOSTNAME || 'localhost'
    });
  }, delay);
});

// [ERROR-3] VERBOSE ERROR HANDLER — Sends full stack to client in all envs.
// Should check: if (process.env.NODE_ENV === 'development')
app.use((err, req, res, next) => {
  logger.error(err.stack);
  res.status(err.statusCode || 500).json({
    message: err.message,
    stack: err.stack, // NEVER send stack to client in production
  });
});

// [ERROR-2] NO GRACEFUL SHUTDOWN — SIGTERM exits immediately.
// Kubernetes sends SIGTERM before killing a pod. Apps should drain
// connections over ~30s. This one drops all in-flight requests instantly.
//
// Correct implementation would be:
//   process.on('SIGTERM', () => { server.close(() => process.exit(0)); });
//
// (No handler registered here — default Node.js behavior is instant exit)

connectDB().then(() => {
  // [ERROR-4] NO SERVER TIMEOUT set on the http.Server instance.
  // Default is 0 (infinite). A stalled DB query holds connections indefinitely.
  const server = app.listen(PORT, () => {
    logger.info(`Server running on port ${PORT}`);
  });
  // server.timeout = 30000; // <-- intentionally missing
});
