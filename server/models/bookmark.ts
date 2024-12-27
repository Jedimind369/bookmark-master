import { db } from "@db";
import { bookmarks, type InsertBookmark, type SelectBookmark } from "@db/schema";
import { eq } from "drizzle-orm";

export class BookmarkModel {
  static async findAll() {
    try {
      return await db.select().from(bookmarks);
    } catch (error) {
      console.error("Error fetching bookmarks:", error);
      throw error;
    }
  }

  static async findById(id: number) {
    try {
      const results = await db
        .select()
        .from(bookmarks)
        .where(eq(bookmarks.id, id))
        .limit(1);
      return results[0] || null;
    } catch (error) {
      console.error("Error fetching bookmark:", error);
      throw error;
    }
  }

  static async create(data: Omit<InsertBookmark, "id" | "dateAdded">) {
    try {
      const [bookmark] = await db
        .insert(bookmarks)
        .values({
          ...data,
          dateAdded: new Date(),
          tags: data.tags || [],
          collections: data.collections || [],
        })
        .returning();
      return bookmark;
    } catch (error) {
      console.error("Error creating bookmark:", error);
      throw error;
    }
  }

  static async update(id: number, data: Partial<Omit<InsertBookmark, "id">>) {
    try {
      const [bookmark] = await db
        .update(bookmarks)
        .set(data)
        .where(eq(bookmarks.id, id))
        .returning();
      return bookmark || null;
    } catch (error) {
      console.error("Error updating bookmark:", error);
      throw error;
    }
  }

  static async delete(id: number) {
    try {
      const [bookmark] = await db
        .delete(bookmarks)
        .where(eq(bookmarks.id, id))
        .returning();
      return !!bookmark;
    } catch (error) {
      console.error("Error deleting bookmark:", error);
      throw error;
    }
  }

  static async bulkCreate(data: Array<Omit<InsertBookmark, "id" | "dateAdded">>) {
    try {
      const now = new Date();
      const bookmarksToInsert = data.map(bookmark => ({
        ...bookmark,
        dateAdded: now,
        tags: bookmark.tags || [],
        collections: bookmark.collections || [],
      }));

      // Use batch size of 1000 for optimal performance
      const batchSize = 1000;
      const results = [];

      for (let i = 0; i < bookmarksToInsert.length; i += batchSize) {
        const batch = bookmarksToInsert.slice(i, i + batchSize);
        const inserted = await db
          .insert(bookmarks)
          .values(batch)
          .returning();
        results.push(...inserted);

        // Add a small delay between batches to prevent overwhelming the database
        if (i + batchSize < bookmarksToInsert.length) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }

      return results;
    } catch (error) {
      console.error("Error bulk creating bookmarks:", error);
      throw error;
    }
  }
}