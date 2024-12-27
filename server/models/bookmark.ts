import { db } from "@db";
import { bookmarks, users, type InsertBookmark, type SelectBookmark, type AnalysisStatus } from "@db/schema";
import { eq, sql, desc } from "drizzle-orm";
import { AIService } from "../services/aiService";

export class BookmarkModel {
  static async findAll() {
    try {
      const results = await db
        .select()
        .from(bookmarks)
        .orderBy(desc(bookmarks.dateModified), desc(bookmarks.dateAdded));

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
      const defaultUserResult = await db.select().from(users).where(eq(users.username, 'default_user')).limit(1);

      if (defaultUserResult.length > 0) {
        return defaultUserResult[0];
      }

      const [defaultUser] = await db.insert(users).values({
        username: 'default_user',
        password: 'not_used',
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
        dateModified: new Date()
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

      // Ensure dateModified is properly converted to a Date object
      const dateModified = typeof data.dateModified === 'string' 
        ? new Date(data.dateModified)
        : new Date();

      const normalizedData = {
        ...data,
        tags: Array.isArray(data.tags) ? data.tags : existing.tags,
        collections: Array.isArray(data.collections) ? data.collections : existing.collections,
        dateModified,
        analysis: data.analysis || existing.analysis,
        updateHistory: [
          ...(existing.updateHistory || []),
          {
            timestamp: new Date().toISOString(),
            changes: data,
            previousState: { ...existing }
          }
        ]
      };

      console.log('[Update] Normalized data:', normalizedData);

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
          sql`analysis IS NULL OR 
              analysis->>'status' IS NULL OR 
              analysis->>'status' NOT IN ('success', 'error', 'invalid_url', 'rate_limited', 'unreachable', 'system_error')`
        );

      return results.length;
    } catch (error) {
      console.error("[Enrichment] Error getting enrichment count:", error);
      return 0;
    }
  }

  static async getProcessedCount() {
    try {
      const results = await db
        .select()
        .from(bookmarks)
        .where(
          sql`analysis IS NOT NULL AND 
              analysis->>'status' IN ('success', 'error', 'invalid_url', 'rate_limited', 'unreachable', 'system_error')`
        );

      return results.length;
    } catch (error) {
      console.error("[Enrichment] Error getting processed count:", error);
      return 0;
    }
  }

  static async enrichAllBookmarks() {
    try {
      const bookmarksToUpdate = await db
        .select()
        .from(bookmarks)
        .where(
          sql`analysis IS NULL OR 
              analysis->>'status' IS NULL OR 
              analysis->>'status' NOT IN ('success', 'error', 'invalid_url', 'rate_limited', 'unreachable', 'system_error')`
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
      console.log(`[Enrichment] Starting analysis for bookmark ${bookmark.id}: ${bookmark.url}`);

      // Update status to processing
      await db
        .update(bookmarks)
        .set({
          analysis: {
            status: 'processing' as AnalysisStatus,
            lastUpdated: new Date().toISOString()
          },
          dateModified: new Date()
        })
        .where(eq(bookmarks.id, bookmark.id));

      try {
        const analysis = await AIService.analyzeUrl(bookmark.url);
        console.log(`[Enrichment] Successfully analyzed bookmark ${bookmark.id}:`, analysis);

        // Store successful analysis
        const [updated] = await db
          .update(bookmarks)
          .set({
            title: analysis.title || bookmark.title, // Use analyzed title if available
            description: analysis.description || bookmark.description, // Use analyzed description if available
            tags: analysis.tags || bookmark.tags || [], // Merge or use analyzed tags
            analysis: {
              status: 'success' as AnalysisStatus,
              lastUpdated: new Date().toISOString(),
              summary: analysis.description,
              tags: analysis.tags,
              title: analysis.title,
              mainTopic: analysis.mainTopic,
              isLandingPage: analysis.isLandingPage,
              metadata: analysis.metadata
            },
            dateModified: new Date()
          })
          .where(eq(bookmarks.id, bookmark.id))
          .returning();

        console.log(`[Enrichment] Updated bookmark ${bookmark.id} with analysis results`);
        return updated;
      } catch (error) {
        console.error(`[Enrichment] Failed to analyze URL for bookmark ${bookmark.id}:`, error);

        let status: AnalysisStatus = 'error';
        let errorSummary = "Failed to analyze this URL";
        let retryable = true;

        if (error instanceof Error) {
          console.log(`[Enrichment] Error type for bookmark ${bookmark.id}:`, error.message);
          if (error.message.includes('Invalid URL')) {
            status = 'invalid_url';
            errorSummary = "Invalid URL format";
            retryable = false;
          } else if (error.message.includes('rate limit')) {
            status = 'rate_limited';
            errorSummary = "Rate limit exceeded";
            retryable = true;
          } else if (error.message.includes('unreachable')) {
            status = 'unreachable';
            errorSummary = "Website unreachable";
            retryable = true;
          }
        }

        // Store error information
        const [updated] = await db
          .update(bookmarks)
          .set({
            analysis: {
              status,
              lastUpdated: new Date().toISOString(),
              summary: errorSummary,
              error: error instanceof Error ? error.message : 'Unknown error',
              retryable
            },
            dateModified: new Date()
          })
          .where(eq(bookmarks.id, bookmark.id))
          .returning();

        return updated;
      }
    } catch (error) {
      console.error(`[Enrichment] Failed to process bookmark ${bookmark.id}:`, error);
      // Mark the bookmark as processed with error
      try {
        const [updated] = await db
          .update(bookmarks)
          .set({
            analysis: {
              status: 'system_error' as AnalysisStatus,
              lastUpdated: new Date().toISOString(),
              summary: "Error processing bookmark",
              error: error instanceof Error ? error.message : 'Unknown error',
              retryable: true
            },
            dateModified: new Date()
          })
          .where(eq(bookmarks.id, bookmark.id))
          .returning();
        return updated;
      } catch (dbError) {
        console.error(`[Enrichment] Failed to update error status for bookmark ${bookmark.id}:`, dbError);
        throw error;
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