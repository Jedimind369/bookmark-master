database: {
  maxConnections: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000
}

monitoring: {
  errorRateThreshold: 0.1,    // 10% error rate threshold
  latencyThreshold: 2000,     // 2 seconds
  memoryThreshold: 512MB      // 512MB memory threshold
}