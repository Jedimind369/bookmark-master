export const performanceConfig = {
    database: {
        maxConnections: 20,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 5000
    },
    api: {
        maxConcurrent: 5,
        minTime: 200,
        reservoir: 50,
        windowMs: 60000, // 1 minute
        maxRequests: 50
    },
    cache: {
        maxItems: 1000,
        ttl: 1800000 // 30 minutes
    },
    monitoring: {
        errorRateThreshold: 0.1, // 10% error rate threshold
        latencyThreshold: 2000, // 2 seconds
        memoryThreshold: 512 * 1024 * 1024 // 512MB
    },
    gc: {
        threshold: 75, // Percentage of heap usage to trigger GC
        interval: 60000 // Check every minute
    },
    maxConcurrentOperations: 5,
    batchSize: 20
};