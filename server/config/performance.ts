
export const performanceConfig = {
  // Memory optimization
  maxConcurrentOperations: 3,
  batchSize: 25,
  cacheTimeout: 900000, // 15 minutes
  
  // Connection pooling
  db: {
    maxConnections: 10,
    idleTimeoutMillis: 20000,
    connectionTimeoutMillis: 5000
  },
  
  // Rate limiting
  api: {
    windowMs: 60000,
    maxRequests: 50,
    delayAfter: 25,
    delayMs: 500
  }
};
