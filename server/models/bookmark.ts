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
}