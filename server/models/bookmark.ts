import { db } from "@db";
import { bookmarks, users, type InsertBookmark, type SelectBookmark } from "@db/schema";
import { eq, sql } from "drizzle-orm";
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

      // Track changes
      const changes: Record<string, any> = {};
      Object.entries(data).forEach(([key, value]) => {
        if (JSON.stringify(existing[key]) !== JSON.stringify(value)) {
          changes[key] = value;
        }
      });

      const updateRecord = {
        timestamp: new Date().toISOString(),
        changes,
        previousState: { ...existing }
      };

      const normalizedData = {
        ...existing,
        title: data.title,
        url: data.url,
        description: data.description,
        tags: Array.isArray(data.tags) ? data.tags : [],
        collections: Array.isArray(data.collections) ? data.collections : [],
        dateModified: new Date(),
        analysis: data.analysis || existing.analysis,
        updateHistory: [...(existing.updateHistory || []), updateRecord]
      };

      console.log('[Update History]', {
        bookmarkId: id,
        changes,
        timestamp: updateRecord.timestamp
      });

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

      // Deduplicate bookmarks by URL
      const uniqueBookmarks = Array.from(
        new Map(data.map(item => [item.url, item])).values()
      );

      console.log(`Processing ${data.length} bookmarks, ${uniqueBookmarks.length} unique URLs`);

      // Transform and validate bookmarks
      const bookmarksToInsert = uniqueBookmarks.map(bookmark => {
        // Ensure URL is valid
        try {
          new URL(bookmark.url);
        } catch (error) {
          console.warn(`Skipping invalid URL: ${bookmark.url}`);
          return null;
        }

        return {
          ...bookmark,
          userId: defaultUser.id,
          title: bookmark.title.slice(0, 255), // Ensure title fits in DB
          description: bookmark.description?.slice(0, 1000) || null, // Limit description length
          tags: Array.isArray(bookmark.tags) ? bookmark.tags : [],
          collections: Array.isArray(bookmark.collections) ? bookmark.collections : [],
        };
      }).filter((bookmark): bookmark is NonNullable<typeof bookmark> => bookmark !== null);

      console.log(`Validated ${bookmarksToInsert.length} bookmarks for insertion`);

      // Use batch size of 100 for optimal performance
      const batchSize = 100;
      const results = [];

      for (let i = 0; i < bookmarksToInsert.length; i += batchSize) {
        const batch = bookmarksToInsert.slice(i, i + batchSize);
        console.log(`Processing batch ${Math.floor(i/batchSize) + 1} of ${Math.ceil(bookmarksToInsert.length/batchSize)}`);

        try {
          const inserted = await db
            .insert(bookmarks)
            .values(batch)
            .returning();
          results.push(...inserted);

          // Add a small delay between batches to prevent overwhelming the database
          if (i + batchSize < bookmarksToInsert.length) {
            await new Promise(resolve => setTimeout(resolve, 100));
          }
        } catch (error) {
          console.error(`Error inserting batch ${Math.floor(i/batchSize) + 1}:`, error);
          // Continue with next batch even if current fails
          continue;
        }
      }

      console.log(`Successfully inserted ${results.length} bookmarks`);
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
          sql`analysis IS NULL OR LENGTH(COALESCE(analysis->>'description', '')) < 100`
        );

      return results.length;
    } catch (error) {
      console.error("Error getting enrichment count:", error);
      return 0;
    }
  }

  static async getProcessedCount() {
    try {
      const results = await db
        .select()
        .from(bookmarks)
        .where(
          sql`analysis IS NOT NULL AND (
            LENGTH(COALESCE(analysis->>'summary', '')) >= 100 
            OR analysis->>'summary' = 'Failed to analyze this URL'
            OR analysis->>'summary' = 'Error processing bookmark'
            OR analysis->>'status' IN ('error', 'invalid_url', 'rate_limited', 'unreachable', 'system_error')
          )`
        );

      return results.length;
    } catch (error) {
      console.error("Error getting processed count:", error);
      return 0;
    }
  }

  static async enrichAllBookmarks() {
    try {
      const bookmarksToUpdate = await db
        .select()
        .from(bookmarks)
        .where(
          sql`analysis IS NULL OR LENGTH(COALESCE(analysis->>'summary', '')) < 100`
        );

      console.log(`[Enrichment] Starting enrichment process for ${bookmarksToUpdate.length} bookmarks`);

      // Process in batches of 3 to avoid overloading
      const batchSize = 3;
      for (let i = 0; i < bookmarksToUpdate.length; i += batchSize) {
        const batch = bookmarksToUpdate.slice(i, i + batchSize);
        console.log(`[Enrichment] Processing batch ${Math.floor(i/batchSize) + 1} of ${Math.ceil(bookmarksToUpdate.length/batchSize)}`);

        // Process each bookmark in the batch sequentially to better track failures
        for (const bookmark of batch) {
          try {
            console.log(`[Enrichment] Processing bookmark ${bookmark.id}: ${bookmark.url}`);
            await this.enrichBookmarkAnalysis(bookmark);
          } catch (error) {
            console.error(`[Enrichment] Error processing bookmark ${bookmark.id}:`, error);
            // Continue with next bookmark even if current one fails
          }
          // Add a small delay between bookmarks
          await new Promise(resolve => setTimeout(resolve, 1000));
        }

        // Add a delay between batches to prevent rate limiting
        if (i + batchSize < bookmarksToUpdate.length) {
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }

      console.log('[Enrichment] Completed enrichment process');
      return true;
    } catch (error) {
      console.error("[Enrichment] Failed to enrich bookmarks:", error);
      return false;
    }
  }

  static async enrichBookmarkAnalysis(bookmark: SelectBookmark) {
    try {
      // Check if bookmark needs enrichment
      const needsEnrichment = !bookmark.analysis ||
                            !bookmark.analysis.summary ||
                            bookmark.analysis.summary.length < 100;

      if (needsEnrichment) {
        console.log(`[Enrichment] Starting analysis for bookmark ${bookmark.id}: ${bookmark.url}`);

        // Update status to processing
        await db
          .update(bookmarks)
          .set({
            analysis: {
              status: 'processing' as const,
              lastUpdated: new Date().toISOString()
            }
          })
          .where(eq(bookmarks.id, bookmark.id));

        try {
          const analysis = await AIService.analyzeUrl(bookmark.url);
          console.log(`[Enrichment] Successfully analyzed bookmark ${bookmark.id}`);

          // Store successful analysis
          const [updated] = await db
            .update(bookmarks)
            .set({
              analysis: {
                summary: analysis.description,
                credibilityScore: 1.0,
                tags: analysis.tags,
                isLandingPage: analysis.isLandingPage,
                mainTopic: analysis.mainTopic,
                lastUpdated: new Date().toISOString(),
                status: 'success' as const
              }
            })
            .where(eq(bookmarks.id, bookmark.id))
            .returning();

          return updated;
        } catch (error) {
          console.error(`[Enrichment] Failed to analyze URL for bookmark ${bookmark.id}:`, error);

          // Categorize the error and store it appropriately
          let errorSummary = "Failed to analyze this URL";
          let errorStatus: 'error' | 'invalid_url' | 'rate_limited' | 'unreachable' | 'system_error' = 'error';
          let retryable = true;

          if (error instanceof Error) {
            console.log(`[Enrichment] Error type for bookmark ${bookmark.id}:`, error.message);
            if (error.message.includes('Invalid URL')) {
              errorSummary = "Invalid URL format";
              errorStatus = 'invalid_url';
              retryable = false;
            } else if (error.message.includes('rate limit')) {
              errorSummary = "Rate limit exceeded";
              errorStatus = 'rate_limited';
              retryable = true;
            } else if (error.message.includes('unreachable')) {
              errorSummary = "Website unreachable";
              errorStatus = 'unreachable';
              retryable = true;
            }
          }

          // Store error information
          const [updated] = await db
            .update(bookmarks)
            .set({
              analysis: {
                summary: errorSummary,
                credibilityScore: 0,
                lastUpdated: new Date().toISOString(),
                status: errorStatus,
                error: error instanceof Error ? error.message : 'Unknown error',
                retryable
              }
            })
            .where(eq(bookmarks.id, bookmark.id))
            .returning();

          return updated;
        }
      }
      return bookmark;
    } catch (error) {
      console.error(`[Enrichment] Failed to process bookmark ${bookmark.id}:`, error);
      // Mark the bookmark as processed with error
      try {
        const [updated] = await db
          .update(bookmarks)
          .set({
            analysis: {
              summary: "Error processing bookmark",
              credibilityScore: 0,
              lastUpdated: new Date().toISOString(),
              status: 'system_error' as const,
              error: error instanceof Error ? error.message : 'Unknown error',
              retryable: true
            }
          })
          .where(eq(bookmarks.id, bookmark.id))
          .returning();
        return updated;
      } catch (dbError) {
        console.error(`[Enrichment] Failed to update error status for bookmark ${bookmark.id}:`, dbError);
        return bookmark;
      }
    }
  }

  static async purgeAll() {
    try {
      await db.delete(bookmarks);
      return true;
    } catch (error) {
      console.error("Error purging bookmarks:", error);
      throw new Error("Failed to purge bookmarks");
    }
  }
}