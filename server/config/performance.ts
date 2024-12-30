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
        windowMs: 60000,
        maxRequests: 100
    },
    scraping: {
        maxConcurrent: 5,
        minTime: 200,
        reservoir: 50,
        windowMs: 60000,
        timeout: 10000
    },
    monitoring: {
        memoryThreshold: 512 * 1024 * 1024, // 512MB
        errorRateThreshold: 0.1,
        latencyThreshold: 2000
    },
    gc: {
        interval: 300000 // 5 minutes
    },
    maxConcurrentOperations: 10,
    batchSize: 50
};