// ============================================================
// config/logger.js
//
// CLOUD/AIOPS ERRORS IN THIS FILE:
//
// [ERROR-8] LOGS TO FILE INSTEAD OF STDOUT:
//   Cloud-native logging requires apps to write to stdout/stderr so
//   that log agents (Fluentd, Filebeat, CloudWatch Agent) can capture them.
//   Writing to a local file means:
//     - Cloud log aggregation (CloudWatch, Stackdriver, DataDog) sees NOTHING
//     - AIOps has no log stream to analyze for anomaly detection
//     - Log file grows indefinitely → disk exhaustion
//
// [ERROR-9] NO LOG ROTATION:
//   The log file is opened in append mode with no size limit or rotation.
//   In a busy production pod, this fills the container's ephemeral disk
//   (typically 1–10GB) within hours/days. When disk is full, the OS
//   returns ENOSPC errors and the entire app crashes.
//   AIOps detects disk usage > threshold and alerts.
// ============================================================

const fs = require('fs');
const path = require('path');

// [ERROR-8] Writing to a FILE instead of stdout.
// Cloud-native: use console.log() / process.stdout.write()
// This file-based approach is invisible to all cloud logging infrastructure.
const logsDir = path.join(__dirname, '..', 'logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true });
}

// [ERROR-9] Append-only, no rotation, no max size.
// A high-traffic app can generate GBs of logs per hour.
const logFile = fs.createWriteStream(
  path.join(logsDir, 'app.log'),
  { flags: 'a' } // append forever — disk will eventually fill
);

const formatMessage = (level, message) => {
  return `[${new Date().toISOString()}] [${level.toUpperCase()}] ${message}\n`;
};

const logger = {
  info: (message) => {
    const entry = formatMessage('info', message);
    logFile.write(entry);        // [ERROR-8] File only — not visible in kubectl logs
    // console.log(entry);       // <-- intentionally not writing to stdout
  },
  error: (message) => {
    const entry = formatMessage('error', message);
    logFile.write(entry);        // [ERROR-8] Errors also go to file, not stderr
    // console.error(entry);     // <-- intentionally not writing to stderr
  },
  warn: (message) => {
    const entry = formatMessage('warn', message);
    logFile.write(entry);
  },
};

module.exports = logger;
