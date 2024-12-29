import { drizzle } from "drizzle-orm/neon-serverless";
import ws from "ws";
import * as schema from "@db/schema";

if (!process.env.DATABASE_URL) {
  throw new Error(
    "DATABASE_URL must be set. Did you forget to provision a database?",
  );
}

// Optimize database connection settings
const dbOptions = {
  schema,
  logger: false, // Disable logging in production
  // Database connection pool settings
  pool: {
    min: 1,               // Minimum connections
    max: 5,               // Maximum connections
    idleTimeoutMillis: 30000, // Close idle connections after 30s
    acquireTimeoutMillis: 5000, // Timeout after 5s if can't acquire connection
    reapIntervalMillis: 1000, // Check for idle connections every 1s
  }
};

export const db = drizzle(process.env.DATABASE_URL, dbOptions);