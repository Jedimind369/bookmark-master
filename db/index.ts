import { drizzle } from "drizzle-orm/neon-serverless";
import { Pool } from "@neondatabase/serverless";
import * as schema from "./schema";

if (!process.env.DATABASE_URL) {
  throw new Error("DATABASE_URL must be set. Did you forget to provision a database?");
}

// Configure connection pool with optimized settings
export function createDbConnection() {
    const sql = postgres(process.env.DATABASE_URL!, {
        max: 10,
        idle_timeout: 20,
        connect_timeout: 5,
        max_lifetime: 60 * 15, // 15 minutes
        onnotice: () => {}, // Disable notice logs
        debug: process.env.NODE_ENV === 'development',
        connection: {
            application_name: 'bookmark_master',
            statement_timeout: 10000, // 10s query timeout
            query_timeout: 10000
        }
    });
    
    return drizzle(sql);
}

const db = createDbConnection();

// Handle cleanup
process.on('SIGTERM', () => {
  db.execute(`SELECT pg_terminate_backend(pg_backend_pid());`); // Added for Neon
  process.exit();
});