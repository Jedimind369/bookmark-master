export const performanceConfig = {
  // Memory optimization - reduced from previous values
  maxConcurrentOperations: 2,
  batchSize: 10,
  cacheTimeout: 300000, // 5 minutes

  // Connection pooling - more aggressive timeouts
  db: {
    maxConnections: 5,
    idleTimeoutMillis: 10000,
    connectionTimeoutMillis: 3000
  },

  // Rate limiting - stricter limits
  api: {
    windowMs: 60000,
    maxRequests: 30,
    delayAfter: 15,
    delayMs: 1000
  },

  // Memory cleanup
  gc: {
    threshold: 75, // Percentage of heap usage to trigger GC
    interval: 60000 // Check every minute
  },

  // Monitoring thresholds
  monitoring: {
    errorRateThreshold: 0.1, // 10% error rate threshold
    latencyThreshold: 2000, // 2 seconds
    memoryThreshold: 512 * 1024 * 1024 // 512MB
  }
};