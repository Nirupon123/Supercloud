require('dotenv').config();
const { NodeSDK } = require("@opentelemetry/sdk-node");
const { getNodeAutoInstrumentations } = require("@opentelemetry/auto-instrumentations-node");
const { OTLPTraceExporter } = require("@opentelemetry/exporter-trace-otlp-http");
const { OTLPLogExporter } = require("@opentelemetry/exporter-logs-otlp-http");
const { OTLPMetricExporter } = require("@opentelemetry/exporter-metrics-otlp-http");
const { Resource } = require("@opentelemetry/resources");
const { ATTR_SERVICE_NAME } = require("@opentelemetry/semantic-conventions");
const { LoggerProvider, BatchLogRecordProcessor } = require("@opentelemetry/sdk-logs");
const { PeriodicExportingMetricReader } = require("@opentelemetry/sdk-metrics");
const { logs } = require("@opentelemetry/api-logs");
const { WinstonInstrumentation } = require("@opentelemetry/instrumentation-winston");

// Create OTLP exporters
const traceExporter = new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT
        ? `${process.env.OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces`
        : "http://localhost:4318/v1/traces",
});

const logExporter = new OTLPLogExporter({
    url: process.env.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT || "http://localhost:4318/v1/logs",
});

const metricExporter = new OTLPMetricExporter({
    url: process.env.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT || "http://localhost:4318/v1/metrics",
});

// Create resource with service name
const resource = new Resource({
    [ATTR_SERVICE_NAME]: process.env.OTEL_SERVICE_NAME || "mern-buggy-app",
});

// Initialize Logger Provider
const loggerProvider = new LoggerProvider({
    resource,
});
loggerProvider.addLogRecordProcessor(new BatchLogRecordProcessor(logExporter));

// Register the logger provider globally
logs.setGlobalLoggerProvider(loggerProvider);

// Initialize Node SDK
const sdk = new NodeSDK({
    resource,
    traceExporter,
    metricReader: new PeriodicExportingMetricReader({
        exporter: metricExporter,
    }),
    instrumentations: [
        getNodeAutoInstrumentations({
            "@opentelemetry/instrumentation-fs": { enabled: false },
        }),
        new WinstonInstrumentation({
            logHook: (span, record) => {
                record["resource.service.name"] = process.env.OTEL_SERVICE_NAME || "mern-buggy-app";
            },
        }),
    ],
});

// Start the SDK
try {
    sdk.start();
    console.log("OpenTelemetry instrumentation initialized successfully");
} catch (error) {
    console.error("Error initializing OpenTelemetry:", error);
}

// Handle graceful shutdown
process.on("SIGTERM", () => {
    sdk.shutdown()
        .then(() => console.log("OpenTelemetry SDK shut down successfully"))
        .catch((error) => console.error("Error shutting down OpenTelemetry:", error))
        .finally(() => process.exit(0));
});

module.exports = { loggerProvider };
