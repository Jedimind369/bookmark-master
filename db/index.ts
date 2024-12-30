import { drizzle } from "drizzle-orm/neon-serverless";
import { Pool } from "@neondatabase/serverless";
import * as schema from "./schema";
import { logger } from "../server/utils/logger";

if (!process.env.DATABASE_URL) {
  throw new Error("DATABASE_URL must be set. Did you forget to provision a database?");
}

// Optimized connection pool configuration
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  maxSize: 10,
  idleTimeout: 20,
  connectionTimeoutMillis: 5000,
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
async function checkConnection() {
  try {
    await pool.query('SELECT 1');
    if (!isHealthy) {
      isHealthy = true;
      logger.info('Database connection restored');
    }
  } catch (error) {
    isHealthy = false;
    logger.error('Database connection check failed:', error);
  }
}

// Regular health checks
setInterval(checkConnection, 30000);

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

export function getConnectionStatus() {
  return {
    isHealthy,
    totalCount: pool.totalCount,
    idleCount: pool.idleCount,
    waitingCount: pool.waitingCount
  };
}