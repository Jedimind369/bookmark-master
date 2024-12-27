import type { Express } from "express";
import { createServer, type Server } from "http";
import { BookmarkModel } from "./models/bookmark";
import { AIService } from "./services/aiService";
import { insertBookmarkSchema } from "@db/schema";
import { parseHtmlBookmarks } from "./utils/bookmarkParser";
import { z } from "zod";

export function registerRoutes(app: Express): Server {
  // AI Analysis endpoint
  app.post("/api/analyze-url", async (req, res) => {
    try {
      const { url } = await z.object({ url: z.string().url() }).parseAsync(req.body);
      const analysis = await AIService.analyzeUrl(url);
      res.json(analysis);
    } catch (error) {
      console.error("Failed to analyze URL:", error);
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          message: "Invalid URL format",
          errors: error.errors
        });
      }
      res.status(500).json({ message: "Failed to analyze URL" });
    }
  });

  // Bookmark routes
  app.get("/api/bookmarks", async (req, res) => {
    try {
      const bookmarks = await BookmarkModel.findAll();
      res.json(bookmarks);
    } catch (error) {
      console.error("Failed to fetch bookmarks:", error);
      res.status(500).json({ message: "Failed to fetch bookmarks" });
    }
  });

  app.post("/api/bookmarks", async (req, res) => {
    try {
      const validatedData = await insertBookmarkSchema
        .omit({ id: true, dateAdded: true, userId: true })
        .parseAsync(req.body);

      // Ensure tags and collections are arrays
      const normalizedData = {
        ...validatedData,
        tags: Array.isArray(validatedData.tags) ? validatedData.tags : [],
        collections: Array.isArray(validatedData.collections) ? validatedData.collections : [],
      };

      const bookmark = await BookmarkModel.create(normalizedData);
      res.status(201).json(bookmark);
    } catch (error) {
      console.error("Failed to create bookmark:", error);
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          message: "Invalid bookmark data",
          errors: error.errors
        });
      }
      res.status(500).json({ message: "Failed to create bookmark" });
    }
  });

  // Bulk import endpoint
  app.post("/api/bookmarks/import", async (req, res) => {
    try {
      console.log(`Received ${req.body.length} bookmarks for import`);

      // Create a schema for import validation
      const importBookmarkSchema = z.object({
        url: z.string().url(),
        title: z.string(),
        description: z.string().optional().nullable(),
        tags: z.array(z.string()).default([]),
        collections: z.array(z.string()).default([])
      });

      // Validate and transform the incoming data
      const bookmarksData = await z.array(importBookmarkSchema).parseAsync(req.body);
      console.log(`Validated ${bookmarksData.length} bookmarks`);

      // Transform the validated data for bulk creation
      const normalizedBookmarks = bookmarksData.map(bookmark => ({
        url: bookmark.url,
        title: bookmark.title,
        description: bookmark.description ?? null,
        tags: bookmark.tags,
        collections: bookmark.collections
      }));

      // Use the bulk create method from BookmarkModel
      const createdBookmarks = await BookmarkModel.bulkCreate(normalizedBookmarks);

      res.status(201).json({
        message: "Bookmarks imported successfully",
        count: createdBookmarks.length,
        totalReceived: req.body.length,
        duplicatesRemoved: req.body.length - createdBookmarks.length
      });
    } catch (error) {
      console.error("Failed to import bookmarks:", error);
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          message: "Invalid bookmark data",
          errors: error.errors
        });
      }
      res.status(500).json({ message: "Failed to import bookmarks" });
    }
  });

  // HTML Bookmark parsing endpoint
  app.post("/api/bookmarks/parse-html", async (req, res) => {
    try {
      console.log("Received HTML content type:", req.get('Content-Type'));
      const htmlContent = req.body;

      if (typeof htmlContent !== 'string' || !htmlContent.trim()) {
        console.error("Invalid HTML content received:", typeof htmlContent);
        return res.status(400).json({ message: "Invalid HTML content" });
      }

      console.log("Parsing HTML content...");
      const bookmarks = parseHtmlBookmarks(htmlContent);
      console.log(`Successfully parsed ${bookmarks.length} bookmarks`);

      // Log sample bookmarks for debugging
      if (bookmarks.length > 0) {
        console.log("Sample bookmark:", JSON.stringify(bookmarks[0], null, 2));
      }

      res.json(bookmarks);
    } catch (error) {
      console.error("Failed to parse HTML bookmarks:", error);
      res.status(500).json({ message: "Failed to parse HTML bookmarks" });
    }
  });

  // Get count of bookmarks that can be enriched
  app.get("/api/bookmarks/enrich/count", async (req, res) => {
    try {
      const count = await BookmarkModel.getEnrichmentCount();
      res.json(count);
    } catch (error) {
      console.error("Failed to get enrichment count:", error);
      res.status(500).json({ message: "Failed to get enrichment count" });
    }
  });

  // Get enrichment status endpoint
  app.get("/api/bookmarks/enrich/status", async (req, res) => {
    try {
      const total = await BookmarkModel.getEnrichmentCount();
      const processed = await BookmarkModel.getProcessedCount();

      let status: "idle" | "processing" | "completed" | "error" = "idle";
      if (total === 0) {
        status = "completed";
      } else if (processed === total) {
        status = "completed";
      } else if (processed < total) {
        status = "processing";
      }

      res.json({
        processedCount: processed,
        totalCount: total,
        status,
        message: status === "completed" 
          ? "All bookmarks have been enriched"
          : `Enriching bookmarks: ${processed} of ${total} processed`
      });
    } catch (error) {
      console.error("Failed to get enrichment status:", error);
      res.status(500).json({ 
        message: "Failed to get enrichment status",
        status: "error"
      });
    }
  });

  // Endpoint to manually enrich bookmarks with comprehensive analysis
  app.post("/api/bookmarks/enrich", async (req, res) => {
    try {
      // Get count of bookmarks that need enrichment
      const count = await BookmarkModel.getEnrichmentCount();

      if (count === 0) {
        return res.json({
          message: "No bookmarks require enrichment",
          count: 0,
          status: "completed"
        });
      }

      // Start the enrichment process
      BookmarkModel.enrichAllBookmarks().catch(error => {
        console.error("Enrichment process failed:", error);
      });

      res.json({ 
        message: `Started enriching ${count} bookmarks with comprehensive analysis`,
        count,
        status: "processing"
      });
    } catch (error) {
      console.error("Failed to start bookmark enrichment:", error);
      res.status(500).json({ message: "Failed to start bookmark enrichment" });
    }
  });

  // Purge all bookmarks endpoint
  app.delete("/api/bookmarks/purge", async (req, res) => {
    try {
      await BookmarkModel.purgeAll();
      res.json({ 
        message: "Successfully purged all bookmarks",
        success: true
      });
    } catch (error) {
      console.error("Failed to purge bookmarks:", error);
      res.status(500).json({ message: "Failed to purge bookmarks" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}