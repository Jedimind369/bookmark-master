import { drizzle } from "drizzle-orm/neon-serverless";
import { Pool } from "@neondatabase/serverless";
import * as schema from "./schema";
import { logger } from "../server/utils/logger";
import { performanceConfig } from "../server/config/performance";

if (!process.env.DATABASE_URL) {
  throw new Error("DATABASE_URL must be set. Did you forget to provision a database?");
}

// Optimized connection pool configuration using performance settings
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  maxSize: performanceConfig.db.maxConnections,
  idleTimeout: performanceConfig.db.idleTimeoutMillis / 1000, // Convert to seconds
  connectionTimeoutMillis: performanceConfig.db.connectionTimeoutMillis,
  maxLifetimeSeconds: 60 * 15, // 15 minutes
  statementTimeout: 10000, // 10s query timeout
});

// Add connection error handling
pool.on('error', (err) => {
  logger.error('Unexpected error on idle client', err);
  process.exit(-1);
});

// Create db instance with connection pool
export const db = drizzle(pool, { schema });

// Monitor connection health
let isHealthy = true;
let lastHealthCheck = Date.now();

async function checkConnection() {
  try {
    const currentTime = Date.now();
    // Only check if enough time has passed since last check
    if (currentTime - lastHealthCheck < performanceConfig.db.idleTimeoutMillis) {
      return;
    }

    await pool.query('SELECT 1');
    lastHealthCheck = currentTime;

    if (!isHealthy) {
      isHealthy = true;
      logger.info('Database connection restored');
    }
  } catch (error) {
    isHealthy = false;
    logger.error('Database connection check failed:', error);

    // Attempt to clean up if threshold exceeded
    if (pool.totalCount > performanceConfig.db.maxConnections) {
      try {
        await pool.end();
        logger.info('Connection pool reset due to threshold exceeded');
      } catch (endError) {
        logger.error('Error ending connection pool:', endError);
      }
    }
  }
}

// Regular health checks with configurable interval
setInterval(checkConnection, performanceConfig.db.idleTimeoutMillis);

// Graceful shutdown handling
process.on('SIGTERM', async () => {
  try {
    await pool.end();
    logger.info('Database pool has ended');
  } catch (error) {
    logger.error('Error during pool shutdown:', error);
  }
  process.exit(0);
});

// Enhanced connection status monitoring
export function getConnectionStatus() {
  return {
    isHealthy,
    totalCount: pool.totalCount,
    idleCount: pool.idleCount,
    waitingCount: pool.waitingCount,
    lastHealthCheck,
    maxConnections: performanceConfig.db.maxConnections,
    currentMemoryUsage: process.memoryUsage().heapUsed
  };
}