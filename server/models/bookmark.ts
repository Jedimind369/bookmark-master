import { db } from "@db";
import { bookmarks, type InsertBookmark, type SelectBookmark } from "@db/schema";
import { eq } from "drizzle-orm";

export class BookmarkModel {
  static async findAll() {
    try {
      const results = await db.select().from(bookmarks);
      return results.map(bookmark => ({
        ...bookmark,
        tags: bookmark.tags || [],
        collections: bookmark.collections || []
      }));
    } catch (error) {
      console.error("Error fetching bookmarks:", error);
      throw new Error("Failed to fetch bookmarks");
    }
  }

  static async findById(id: number) {
    try {
      const results = await db
        .select()
        .from(bookmarks)
        .where(eq(bookmarks.id, id))
        .limit(1);

      if (!results.length) return null;

      const bookmark = results[0];
      return {
        ...bookmark,
        tags: bookmark.tags || [],
        collections: bookmark.collections || []
      };
    } catch (error) {
      console.error("Error fetching bookmark:", error);
      throw new Error(`Failed to fetch bookmark with id ${id}`);
    }
  }

  static async create(data: Omit<InsertBookmark, "id" | "dateAdded" | "userId">) {
    try {
      // Get default user id
      const [defaultUser] = await db.execute<{ id: number }>(
        "SELECT id FROM users WHERE username = 'default_user' LIMIT 1"
      );

      if (!defaultUser) {
        throw new Error("Default user not found");
      }

      // Ensure tags and collections are arrays
      const normalizedData = {
        ...data,
        userId: defaultUser.id,
        dateAdded: new Date(),
        tags: Array.isArray(data.tags) ? data.tags : [],
        collections: Array.isArray(data.collections) ? data.collections : [],
      };

      const [bookmark] = await db
        .insert(bookmarks)
        .values(normalizedData)
        .returning();

      return bookmark;
    } catch (error) {
      console.error("Error creating bookmark:", error);
      throw new Error("Failed to create bookmark");
    }
  }

  static async update(id: number, data: Partial<Omit<InsertBookmark, "id">>) {
    try {
      // First check if bookmark exists
      const existing = await this.findById(id);
      if (!existing) {
        throw new Error(`Bookmark with id ${id} not found`);
      }

      // Normalize arrays
      const normalizedData = {
        ...data,
        tags: data.tags !== undefined ? (Array.isArray(data.tags) ? data.tags : []) : undefined,
        collections: data.collections !== undefined ? (Array.isArray(data.collections) ? data.collections : []) : undefined,
      };

      const [bookmark] = await db
        .update(bookmarks)
        .set(normalizedData)
        .where(eq(bookmarks.id, id))
        .returning();

      return bookmark;
    } catch (error) {
      console.error("Error updating bookmark:", error);
      if (error instanceof Error) throw error;
      throw new Error(`Failed to update bookmark with id ${id}`);
    }
  }

  static async delete(id: number) {
    try {
      // First check if bookmark exists
      const existing = await this.findById(id);
      if (!existing) {
        throw new Error(`Bookmark with id ${id} not found`);
      }

      const [bookmark] = await db
        .delete(bookmarks)
        .where(eq(bookmarks.id, id))
        .returning();

      return true;
    } catch (error) {
      console.error("Error deleting bookmark:", error);
      if (error instanceof Error) throw error;
      throw new Error(`Failed to delete bookmark with id ${id}`);
    }
  }

  static async bulkCreate(data: Array<Omit<InsertBookmark, "id" | "dateAdded" | "userId">>) {
    try {
      // Get default user id
      const [defaultUser] = await db.execute<{ id: number }>(
        "SELECT id FROM users WHERE username = 'default_user' LIMIT 1"
      );

      if (!defaultUser) {
        throw new Error("Default user not found");
      }

      const now = new Date();
      const bookmarksToInsert = data.map(bookmark => ({
        ...bookmark,
        userId: defaultUser.id,
        dateAdded: now,
        tags: Array.isArray(bookmark.tags) ? bookmark.tags : [],
        collections: Array.isArray(bookmark.collections) ? bookmark.collections : [],
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
      throw new Error("Failed to bulk create bookmarks");
    }
  }
}