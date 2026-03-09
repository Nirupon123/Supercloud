import { LoggerProvider, BatchLogRecordProcessor } from '@opentelemetry/sdk-logs';
import { OTLPLogExporter } from '@opentelemetry/exporter-logs-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME } from '@opentelemetry/semantic-conventions';
import { logs, SeverityNumber } from '@opentelemetry/api-logs';

const initializeOTel = () => {
    const resource = new Resource({
        [ATTR_SERVICE_NAME]: 'frontend-browser',
    });

    const logExporter = new OTLPLogExporter({
        url: 'http://localhost:4318/v1/logs', // This must be reachable from the browser
    });

    const loggerProvider = new LoggerProvider({
        resource,
    });

    loggerProvider.addLogRecordProcessor(new BatchLogRecordProcessor(logExporter));

    logs.setGlobalLoggerProvider(loggerProvider);

    const logger = logs.getLogger('frontend-logger');

    // Simple bridge to capture console logs
    const originalLog = console.log;
    const originalError = console.error;
    const originalWarn = console.warn;

    console.log = (...args) => {
        logger.emit({
            severityNumber: SeverityNumber.INFO,
            severityText: 'INFO',
            body: args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg) : arg)).join(' '),
        });
        originalLog.apply(console, args);
    };

    console.error = (...args) => {
        logger.emit({
            severityNumber: SeverityNumber.ERROR,
            severityText: 'ERROR',
            body: args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg) : arg)).join(' '),
        });
        originalError.apply(console, args);
    };

    console.warn = (...args) => {
        logger.emit({
            severityNumber: SeverityNumber.WARN,
            severityText: 'WARN',
            body: args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg) : arg)).join(' '),
        });
        originalWarn.apply(console, args);
    };

    console.info("Frontend OpenTelemetry logging initialized");
};

export default initializeOTel;
