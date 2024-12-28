import { drizzle } from "drizzle-orm/neon-serverless";
import { neon, neonConfig } from '@neondatabase/serverless';
import { sql } from "drizzle-orm";
import * as schema from "@db/schema";
import ws from 'ws';

if (!process.env.DATABASE_URL) {
  throw new Error(
    "DATABASE_URL must be set. Did you forget to provision a database?",
  );
}

// Configure neon with WebSocket fallback
neonConfig.webSocketConstructor = ws;
const sql_connection = neon(process.env.DATABASE_URL);

// Configure database with proper error handling
export const db = drizzle(sql_connection, { 
  schema,
  logger: {
    logQuery: (query: string, params: any[]) => {
      console.log('[Database] Query:', query);
      console.log('[Database] Params:', params);
    }
  }
});

// Export connection test function with better error handling
export async function testDatabaseConnection() {
  try {
    console.log('[Database] Testing database connection...');
    // Test query that should always work
    const result = await db.execute(sql`SELECT current_timestamp, current_database()`);
    console.log('[Database] Connection successful:', result);

    // Verify schema existence
    const tables = await db.execute(sql`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public'
    `);
    console.log('[Database] Existing tables:', tables);

    return true;
  } catch (error) {
    console.error('[Database] Connection test failed:', error);
    // Add detailed error information for debugging
    if (error instanceof Error) {
      console.error('[Database] Error details:', {
        message: error.message,
        stack: error.stack,
        name: error.name
      });
    }

    // Re-throw the error to be handled by the server startup
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