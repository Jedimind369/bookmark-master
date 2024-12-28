import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "@db/schema";

if (!process.env.DATABASE_URL) {
  throw new Error(
    "DATABASE_URL must be set. Did you forget to provision a database?",
  );
}

// Simple postgres.js connection with basic configuration
const client = postgres(process.env.DATABASE_URL, {
  max: 1, // Use a single connection for better stability
  idle_timeout: 20, // Close idle connections after 20 seconds
  connect_timeout: 10, // Connection timeout of 10 seconds
});

export const db = drizzle(client, { schema });

// Export connection test function with better error handling
export async function testDatabaseConnection() {
  try {
    console.log('[Database] Testing database connection...');
    // Simple test query
    await db.execute(sql`SELECT 1`);
    console.log('[Database] Connection successful');
    return true;
  } catch (error) {
    console.error('[Database] Connection test failed:', error);
    throw error;
  }
}

// Initialize database tables
export async function initializeDatabase() {
  try {
    console.log('[Database] Starting database initialization...');

    // Create tables if they don't exist using SQL directly for initial setup
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS bookmarks (
        id SERIAL PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        tags JSONB DEFAULT '[]'::jsonb,
        collections JSONB DEFAULT '[]'::jsonb,
        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date_modified TIMESTAMP,
        analysis JSONB,
        update_history JSONB DEFAULT '[]'::jsonb
      );
    `);

    console.log('[Database] Database initialization completed successfully');
    return true;
  } catch (error) {
    console.error('[Database] Initialization failed:', error);
    throw error;
  }
}