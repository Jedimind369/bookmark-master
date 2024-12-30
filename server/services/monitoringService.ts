import { performanceMonitor } from "../utils/monitoring";
import express from "express";
import statusMonitor from "express-status-monitor";
import client from "prom-client";

// Initialize Prometheus metrics
const register = new client.Registry();
client.collectDefaultMetrics({ register });

// Custom metrics
const httpRequestDurationMicroseconds = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'code'],
  buckets: [0.1, 0.5, 1, 2, 5]
});

const bookmarksTotal = new client.Gauge({
  name: 'bookmarks_total',
  help: 'Total number of bookmarks in the system'
});

const aiProcessingDuration = new client.Histogram({
  name: 'ai_processing_duration_seconds',
  help: 'Duration of AI processing tasks in seconds',
  buckets: [1, 5, 10, 30, 60]
});

register.registerMetric(httpRequestDurationMicroseconds);
register.registerMetric(bookmarksTotal);
register.registerMetric(aiProcessingDuration);

// Configure status monitor options
const statusMonitorConfig = {
  title: 'Bookmark Master Status',
  path: '/status',
  spans: [{
    interval: 1,     // Every second
    retention: 60    // Keep 60 datapoints (1 minute)
  }, {
    interval: 5,     // Every 5 seconds
    retention: 60    // Keep 60 datapoints (5 minutes)
  }, {
    interval: 15,    // Every 15 seconds
    retention: 60    // Keep 60 datapoints (15 minutes)
  }],
  chartVisibility: {
    cpu: true,
    mem: true,
    load: true,
    responseTime: true,
    rps: true,
    statusCodes: true
  },
  healthChecks: [{
    protocol: 'http',
    host: '0.0.0.0',
    path: '/api/bookmarks/health',
    port: '5000'
  }]
};

export function setupMonitoring(app: express.Application) {
  // Add status monitor middleware
  app.use(statusMonitor(statusMonitorConfig));

  // Add Prometheus metrics endpoint
  app.get('/metrics', async (_req, res) => {
    try {
      res.set('Content-Type', register.contentType);
      res.end(await register.metrics());
    } catch (err) {
      res.status(500).end(err);
    }
  });

  // Add route for detailed metrics
  app.get('/api/monitoring/detailed', (_req, res) => {
    const metrics = performanceMonitor.getLatestMetrics();
    const history = performanceMonitor.getMetricsHistory();

    res.json({
      current: metrics,
      history: history.slice(-10), // Last 10 metrics points
      status: {
        uptime: process.uptime(),
        timestamp: Date.now(),
        pid: process.pid,
        memoryUsage: process.memoryUsage(),
        resourceUsage: process.resourceUsage(),
        prometheusMetrics: {
          bookmarksTotal: bookmarksTotal.get(),
          requestDurationP95: httpRequestDurationMicroseconds.get().values[0].value
        }
      }
    });
  });

  // Middleware to track request durations
  app.use((req, res, next) => {
    const start = Date.now();
    res.on('finish', () => {
      const duration = Date.now() - start;
      httpRequestDurationMicroseconds
        .labels(req.method, req.route?.path || req.path, res.statusCode.toString())
        .observe(duration / 1000); // Convert to seconds
    });
    next();
  });
}

// Export metrics for use in other parts of the application
export const memoryUsage = new client.Gauge({
  name: 'memory_usage_bytes',
  help: 'Memory usage in bytes',
  labelNames: ['type']
});

const connectionGauge = new client.Gauge({
  name: 'active_connections',
  help: 'Number of active database connections'
});

const metrics = {
  httpRequestDurationMicroseconds,
  bookmarksTotal,
  aiProcessingDuration,
  memoryUsage,
  connectionGauge
};

// Monitor memory usage
setInterval(() => {
  const mem = process.memoryUsage();
  memoryUsage.labels('heapUsed').set(mem.heapUsed);
  memoryUsage.labels('heapTotal').set(mem.heapTotal);
  memoryUsage.labels('rss').set(mem.rss);
}, 30000);