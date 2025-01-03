import { db } from "@db";
import { bookmarks, users, type InsertBookmark, type SelectBookmark, type AnalysisStatus } from "@db/schema";
import { eq, sql, desc, isNull, or, and } from "drizzle-orm";
import { AIService } from "../services/aiService";

export class BookmarkModel {
  private static async getOrCreateDefaultUser() {
    try {
      console.log('[User] Looking up default user');
      const defaultUserResult = await db.select().from(users).where(eq(users.username, 'default_user')).limit(1);

      if (defaultUserResult.length > 0) {
        console.log('[User] Found existing default user');
        return defaultUserResult[0];
      }

      console.log('[User] Creating default user');
      const [defaultUser] = await db.insert(users).values({
        username: 'default_user',
        password: 'not_used_password'
      }).returning();

      console.log('[User] Created default user:', defaultUser);
      return defaultUser;
    } catch (error) {
      console.error("Error getting/creating default user:", error);
      throw new Error("Failed to get/create default user");
    }
  }

  static async create(data: Omit<InsertBookmark, "id" | "dateAdded" | "userId">) {
    try {
      // Create default user first
      const defaultUser = await this.getOrCreateDefaultUser();
      console.log('[Create] Default user:', defaultUser);

      // Ensure we have a valid user before proceeding
      if (!defaultUser?.id) {
        throw new Error('Failed to get or create default user');
      }

      const normalizedData = {
        ...data,
        userId: defaultUser.id,
        tags: Array.isArray(data.tags) ? data.tags : [],
        collections: Array.isArray(data.collections) ? data.collections : [],
        dateAdded: new Date(),
        dateModified: new Date()
      };

      console.log('[Create] Normalized data:', normalizedData);

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

  static async findAll() {
    try {
      const results = await db
        .select()
        .from(bookmarks)
        .orderBy(sql`${bookmarks.dateModified} DESC, ${bookmarks.dateAdded} DESC`);

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

  static async update(id: number, data: Partial<Omit<InsertBookmark, "id">>) {
    try {
      const existing = await this.findById(id);
      if (!existing) {
        throw new Error(`Bookmark with id ${id} not found`);
      }

      // Simplify the update data structure
      const normalizedData = {
        ...data,
        tags: Array.isArray(data.tags) ? data.tags : existing.tags,
        collections: Array.isArray(data.collections) ? data.collections : existing.collections,
        dateModified: new Date(),
        analysis: data.analysis || existing.analysis
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
          userId: defaultUser.id,
          url: bookmark.url,
          title: (bookmark.title || '').slice(0, 255), // Ensure title fits in DB
          description: (bookmark.description || '').slice(0, 1000) || null, // Limit description length
          tags: Array.isArray(bookmark.tags) ? bookmark.tags : [],
          collections: Array.isArray(bookmark.collections) ? bookmark.collections : [],
          dateAdded: now,
          dateModified: now
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

        // Store successful analysis with quality metrics
        const [updated] = await db
          .update(bookmarks)
          .set({
            title: analysis.recommendations?.improvedTitle || analysis.title || bookmark.title,
            description: analysis.recommendations?.improvedDescription || analysis.description || bookmark.description,
            tags: analysis.recommendations?.suggestedTags || analysis.tags || bookmark.tags || [],
            analysis: {
              status: 'success' as AnalysisStatus,
              lastUpdated: new Date().toISOString(),
              summary: analysis.description,
              contentQuality: analysis.contentQuality,
              mainTopics: analysis.mainTopics,
              recommendations: analysis.recommendations,
              tags: analysis.tags,
              retryable: false
            },
            dateModified: new Date()
          })
          .where(eq(bookmarks.id, bookmark.id))
          .returning();

        console.log(`[Enrichment] Updated bookmark ${bookmark.id} with enhanced analysis results`);
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
              retryable,
              contentQuality: {
                relevance: 0,
                informativeness: 0,
                credibility: 0,
                overallScore: 0
              }
            },
            dateModified: new Date()
          })
          .where(eq(bookmarks.id, bookmark.id))
          .returning();

        return updated;
      }
    } catch (error) {
      console.error(`[Enrichment] Failed to process bookmark ${bookmark.id}:`, error);
      try {
        const [updated] = await db
          .update(bookmarks)
          .set({
            analysis: {
              status: 'system_error' as AnalysisStatus,
              lastUpdated: new Date().toISOString(),
              summary: "Error processing bookmark",
              error: error instanceof Error ? error.message : 'Unknown error',
              retryable: true,
              contentQuality: {
                relevance: 0,
                informativeness: 0,
                credibility: 0,
                overallScore: 0
              }
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

  static async getEnrichmentCount(): Promise<number> {
    try {
      console.log('[Enrichment] Getting enrichment count');
      // Get count of bookmarks that need enrichment (no analysis, processing, error, or low quality)
      const results = await db
        .select({ count: sql<number>`count(*)::int` })
        .from(bookmarks)
        .where(
          or(
            isNull(bookmarks.analysis),
            sql`${bookmarks.analysis}->>'status' = 'processing'`,
            sql`${bookmarks.analysis}->>'status' = 'error'`,
            sql`${bookmarks.analysis}->>'status' = 'success' AND (${bookmarks.analysis}->'contentQuality'->>'overallScore')::float < 0.6`
          )
        );

      const count = results[0]?.count || 0;
      console.log('[Enrichment] Count:', count);
      return count;
    } catch (error) {
      console.error("[Enrichment] Error getting enrichment count:", error);
      throw new Error("Failed to get enrichment count");
    }
  }

  static async getProcessedCount(): Promise<number> {
    try {
      // Get count of successfully processed bookmarks
      const results = await db
        .select({ count: sql<number>`count(*)::int` })
        .from(bookmarks)
        .where(
          and(
            sql`${bookmarks.analysis} is not null`,
            sql`${bookmarks.analysis}->>'status' != 'processing'`
          )
        );

      return results[0]?.count || 0;
    } catch (error) {
      console.error("[Enrichment] Error getting processed count:", error);
      throw new Error("Failed to get processed count");
    }
  }

  static async getTotalBookmarkCount(): Promise<number> {
    try {
      const results = await db
        .select({ count: sql<number>`count(*)::int` })
        .from(bookmarks);

      return results[0]?.count || 0;
    } catch (error) {
      console.error("[Enrichment] Error getting total count:", error);
      throw new Error("Failed to get total count");
    }
  }

  static async enrichAllBookmarks(): Promise<boolean> {
    try {
      const bookmarksToUpdate = await db
        .select()
        .from(bookmarks)
        .where(
          or(
            isNull(bookmarks.analysis),
            sql`${bookmarks.analysis}->>'status' = 'processing'`,
            sql`${bookmarks.analysis}->>'status' = 'error'`,
            sql`${bookmarks.analysis}->>'status' = 'system_error'`
          )
        );

      console.log(`[Enrichment] Starting enrichment process for ${bookmarksToUpdate.length} bookmarks`);

      // Process in larger batches for better throughput
      const batchSize = 10;
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
          // Add a small delay between bookmarks to prevent rate limiting
          await new Promise(resolve => setTimeout(resolve, 1000));
        }

        // Add a delay between batches to prevent overwhelming the system
        if (i + batchSize < bookmarksToUpdate.length) {
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }

      console.log('[Enrichment] Completed enrichment process');
      return true;
    } catch (error) {
      console.error("[Enrichment] Failed to enrich bookmarks:", error);
      throw new Error("Failed to enrich bookmarks");
    }
  }
}