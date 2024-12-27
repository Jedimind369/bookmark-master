import { db } from "@db";
import { bookmarks, users, type InsertBookmark, type SelectBookmark } from "@db/schema";
import { eq, sql, isNull, COALESCE } from "drizzle-orm";
import { AIService } from "../services/aiService";

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

  private static async getOrCreateDefaultUser() {
    try {
      // Try to find default user
      const defaultUserResult = await db.select().from(users).where(eq(users.username, 'default_user')).limit(1);

      if (defaultUserResult.length > 0) {
        return defaultUserResult[0];
      }

      // Create default user if not found
      const [defaultUser] = await db.insert(users).values({
        username: 'default_user',
        password: 'not_used', // We don't use password auth for default user
      }).returning();

      return defaultUser;
    } catch (error) {
      console.error("Error getting/creating default user:", error);
      throw new Error("Failed to get/create default user");
    }
  }

  static async create(data: Omit<InsertBookmark, "id" | "dateAdded" | "userId">) {
    try {
      const defaultUser = await this.getOrCreateDefaultUser();

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
      const existing = await this.findById(id);
      if (!existing) {
        throw new Error(`Bookmark with id ${id} not found`);
      }

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
      const existing = await this.findById(id);
      if (!existing) {
        return false;
      }

      await db.delete(bookmarks).where(eq(bookmarks.id, id));
      return true;
    } catch (error) {
      console.error("Error deleting bookmark:", error);
      throw new Error(`Failed to delete bookmark with id ${id}`);
    }
  }

  static async bulkCreate(data: Array<Omit<InsertBookmark, "id" | "dateAdded" | "userId">>) {
    try {
      const defaultUser = await this.getOrCreateDefaultUser();
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

  static async getEnrichmentCount() {
    try {
      const results = await db
        .select()
        .from(bookmarks)
        .where(
          sql`(analysis IS NULL) OR 
              (analysis->>'description' IS NULL OR LENGTH(COALESCE(analysis->>'description', '')) < 100)`
        );

      return results.length;
    } catch (error) {
      console.error("Error getting enrichment count:", error);
      return 0;
    }
  }

  static async enrichBookmarkAnalysis(bookmark: SelectBookmark) {
    try {
      // Check if bookmark needs enrichment
      const needsEnrichment = !bookmark.analysis ||
                            !bookmark.analysis.summary ||
                            bookmark.analysis.summary.length < 100;

      if (needsEnrichment) {
        console.log(`Enriching analysis for bookmark ${bookmark.id}: ${bookmark.url}`);
        const analysis = await AIService.analyzeUrl(bookmark.url);

        const [updated] = await db
          .update(bookmarks)
          .set({
            analysis: {
              summary: analysis.description,
              credibilityScore: 1.0 // Default score, can be enhanced later
            }
          })
          .where(eq(bookmarks.id, bookmark.id))
          .returning();

        return updated;
      }
      return bookmark;
    } catch (error) {
      console.error(`Failed to enrich bookmark ${bookmark.id}:`, error);
      return bookmark;
    }
  }

  static async enrichAllBookmarks() {
    try {
      const bookmarksToUpdate = await db
        .select()
        .from(bookmarks)
        .where(isNull(bookmarks.analysis));

      console.log(`Found ${bookmarksToUpdate.length} bookmarks to enrich with analysis`);

      // Process in batches of 5 to avoid overloading
      const batchSize = 5;
      for (let i = 0; i < bookmarksToUpdate.length; i += batchSize) {
        const batch = bookmarksToUpdate.slice(i, i + batchSize);
        await Promise.all(batch.map(bookmark => this.enrichBookmarkAnalysis(bookmark)));

        // Add a delay between batches to prevent rate limiting
        if (i + batchSize < bookmarksToUpdate.length) {
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }

      return true;
    } catch (error) {
      console.error("Failed to enrich bookmarks:", error);
      return false;
    }
  }
}