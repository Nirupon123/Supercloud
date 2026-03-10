const winston = require("winston");
const { OpenTelemetryTransportV3 } = require("@opentelemetry/winston-transport");

const serviceName = process.env.OTEL_SERVICE_NAME || "mern-backend";

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || "info",

  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),

  defaultMeta: {
    service_name: serviceName
  },

  transports: [
    new winston.transports.Console(),

    // Send logs to OpenTelemetry → SigNoz
    new OpenTelemetryTransportV3({
      resourceAttributes: {
        "service.name": serviceName
      }
    })
  ]
});


// Structured HTTP log format for Morgan
logger.stream = {
  write: (message) => {
    logger.info({
      event: "http_request",
      message: message.trim()
    });
  }
};


// Helper log functions for better structured logs
logger.api = (endpoint, status, latency) => {
  logger.info({
    event: "api_request",
    endpoint,
    status,
    latency_ms: latency
  });
};

logger.errorLog = (error, context = {}) => {
  logger.error({
    event: "application_error",
    message: error.message,
    stack: error.stack,
    ...context
  });
};

logger.cache = (key, hit) => {
  logger.info({
    event: "cache",
    cache_key: key,
    hit
  });
};

module.exports = logger;