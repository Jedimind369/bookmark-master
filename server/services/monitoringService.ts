import { performanceMonitor } from "../utils/monitoring";
import express from "express";
import statusMonitor from "express-status-monitor";
import client from "prom-client";
import { performanceConfig } from "../config/performance";

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

const memoryUsage = new client.Gauge({
  name: 'memory_usage_bytes',
  help: 'Memory usage in bytes',
  labelNames: ['type']
});

const connectionGauge = new client.Gauge({
  name: 'active_connections',
  help: 'Number of active database connections'
});

register.registerMetric(httpRequestDurationMicroseconds);
register.registerMetric(bookmarksTotal);
register.registerMetric(aiProcessingDuration);
register.registerMetric(memoryUsage);
register.registerMetric(connectionGauge);

// Configure status monitor with performance thresholds
const statusMonitorConfig = {
  title: 'Bookmark Master Status',
  path: '/status',
  spans: [{
    interval: 1,     // Every second
    retention: 60    // Keep 60 datapoints (1 minute)
  }, {
    interval: 5,     // Every 5 seconds
    retention: 60    // Keep 60 datapoints (5 minutes)
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
  }],
  // Add performance thresholds
  thresholds: {
    cpu: performanceConfig.monitoring.memoryThreshold,
    memory: performanceConfig.monitoring.memoryThreshold,
    latency: performanceConfig.monitoring.latencyThreshold
  }
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
        memoryUsage: process.memoryUsage(),
        resourceUsage: process.resourceUsage(),
        thresholds: {
          memory: performanceConfig.monitoring.memoryThreshold,
          latency: performanceConfig.monitoring.latencyThreshold,
          errorRate: performanceConfig.monitoring.errorRateThreshold
        }
      }
    });
  });

  // Middleware to track request durations and memory usage
  app.use((req, res, next) => {
    const start = Date.now();

    // Track memory before request
    const memBefore = process.memoryUsage();

    res.on('finish', () => {
      const duration = Date.now() - start;
      const memAfter = process.memoryUsage();

      // Update metrics
      httpRequestDurationMicroseconds
        .labels(req.method, req.route?.path || req.path, res.statusCode.toString())
        .observe(duration / 1000);

      memoryUsage.labels('heapUsed').set(memAfter.heapUsed);
      memoryUsage.labels('heapTotal').set(memAfter.heapTotal);
      memoryUsage.labels('rss').set(memAfter.rss);

      // Check thresholds
      if (memAfter.heapUsed > performanceConfig.monitoring.memoryThreshold) {
        console.warn(`Memory usage exceeded threshold: ${memAfter.heapUsed} bytes`);
        if (global.gc) {
          global.gc();
        }
      }
    });

    next();
  });

  // Regular memory monitoring
  setInterval(() => {
    const mem = process.memoryUsage();
    Object.entries(mem).forEach(([key, value]) => {
      memoryUsage.labels(key).set(value);
    });
  }, performanceConfig.gc.interval);
}

// Export metrics for use in other parts of the application
export const metrics = {
  httpRequestDurationMicroseconds,
  bookmarksTotal,
  aiProcessingDuration,
  memoryUsage,
  connectionGauge
};