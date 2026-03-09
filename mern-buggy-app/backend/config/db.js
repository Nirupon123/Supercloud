// ============================================================
// config/db.js
//
// CLOUD/AIOPS ERRORS IN THIS FILE:
//
// [ERROR-5] CONNECTION POOL EXHAUSTION: maxPoolSize set to 1.
//   Under any concurrent load (>1 simultaneous request), additional
//   requests queue waiting for a connection. Queue grows unboundedly.
//   AIOps detects p99 latency spike and connection wait time metric.
//
// [ERROR-6] NO RETRY LOGIC: Single connection attempt with no retry.
//   Transient network blip during pod startup (common in cloud) causes
//   permanent startup failure. Pod enters CrashLoopBackOff.
//   AIOps detects startup failure pattern, triggers retry remediation.
//
// [ERROR-7] AGGRESSIVE TIMEOUT: serverSelectionTimeoutMS set to 100ms.
//   In cloud environments with cross-AZ or cross-region DB, 100ms is
//   too tight. Any network jitter causes immediate connection failure.
//   AIOps detects timeout error rate spike, adjusts timeout config.
// ============================================================

const mongoose = require('mongoose');
const logger = require('./logger');

const connectDB = async () => {
  const mongoURI = process.env.MONGO_URI;

  if (!mongoURI) {
    logger.error('FATAL: MONGO_URI environment variable is not set.');
    process.exit(1);
  }

  // [ERROR-6] NO RETRY: Single attempt. Transient failures during cloud
  // startup (DNS not ready, network policy not applied yet) = permanent crash.
  // Should use exponential backoff retry loop.
  try {
    const conn = await mongoose.connect(mongoURI, {
      // [ERROR-5] maxPoolSize = 1: Effectively serializes ALL database operations.
      // Even 2 concurrent requests will cause one to wait in queue.
      // Production apps typically use 10–100 connections per pod.
      maxPoolSize: 1, // Should be: maxPoolSize: 10

      // [ERROR-7] serverSelectionTimeoutMS = 100ms is far too aggressive.
      // Cloud MongoDB (Atlas, DocumentDB) has ~few ms baseline latency.
      // Cross-region setups easily exceed 100ms, causing constant failures.
      serverSelectionTimeoutMS: 100, // Should be: 5000 or 10000

      // No socketTimeoutMS set — once connected, a stalled query waits forever
    });

    logger.info(`MongoDB Connected: ${conn.connection.host}`);
  } catch (error) {
    // [ERROR-6 continued] After single failure, process exits—no retry attempted
    logger.error(`MongoDB connection failed: ${error.message}`);
    process.exit(1);
  }
};

module.exports = connectDB;
