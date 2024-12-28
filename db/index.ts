import { drizzle } from "drizzle-orm/neon-serverless";
import { sql } from "drizzle-orm";
import ws from "ws";
import * as schema from "@db/schema";

if (!process.env.DATABASE_URL) {
  throw new Error(
    "DATABASE_URL must be set. Did you forget to provision a database?",
  );
}

export const db = drizzle(process.env.DATABASE_URL, { 
  schema,
  logger: true,
  connectionOptions: {
    WebSocket: ws,
    keepAlive: true,
    keepAliveTimeout: 10000,
    maxUses: 7 * 24 * 60 * 60,
    maxLifetime: 7 * 24 * 60 * 60,
    retries: 3,
  }
});

// Export connection test function with better error handling
export async function testDatabaseConnection() {
  try {
    console.log('Query:', 'SELECT 1');
    const result = await db.execute(sql`SELECT 1`);
    return true;
  } catch (error) {
    console.error('Database connection test failed:', error);
    // Add detailed error information for debugging
    if (error instanceof Error) {
      console.error('Error details:', {
        message: error.message,
        stack: error.stack,
        name: error.name
      });
    }
    return false;
  }
}