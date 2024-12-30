
import { sql } from 'drizzle-orm';
import { db } from '../db';

async function main() {
  try {
    await db.execute(sql`
      ALTER TABLE bookmarks 
      ADD COLUMN IF NOT EXISTS update_history JSONB DEFAULT '[]';
    `);
    console.log('Migration completed successfully');
  } catch (error) {
    console.error('Migration failed:', error);
    process.exit(1);
  }
  process.exit(0);
}

main();
