const performanceConfig = {
  database: {
    maxConnections: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000
  },
  api: {
    maxConcurrent: 5,
    minTime: 200,
    reservoir: 50,
    windowMs: 60000 // 1 minute
  },
  monitoring: {
    memoryThreshold: 512 * 1024 * 1024,  // 512MB
    errorRateThreshold: 0.1,              // 10%
    latencyThreshold: 2000                // 2s
  }
};