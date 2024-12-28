import { drizzle } from "drizzle-orm/neon-serverless";
import { sql } from "drizzle-orm";
import ws from "ws";
import * as schema from "@db/schema";

if (!process.env.DATABASE_URL) {
  throw new Error(
    "DATABASE_URL must be set. Did you forget to provision a database?",
  );
}

// Configure database with Neon serverless driver
export const db = drizzle({
  connection: process.env.DATABASE_URL,
  schema,
  logger: {
    logQuery: (query: string, params: any[]) => {
      console.log('Query:', query);
      console.log('Params:', params);
    },
  },
  ws
});

// Export connection test function with better error handling
export async function testDatabaseConnection() {
  try {
    console.log('Testing database connection...');
    // Test query that should always work
    const result = await db.execute(sql`SELECT current_timestamp`);
    console.log('Database connection successful:', result);
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