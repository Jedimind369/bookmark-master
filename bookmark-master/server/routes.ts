import type { Express } from "express";
import { createServer, type Server } from "http";
import { BookmarkModel } from "./models/bookmark";
import { AIService } from "./services/aiService";
import { insertBookmarkSchema } from "@db/schema";
import { parseHtmlBookmarks } from "./utils/bookmarkParser";
import { db } from "@db";
import { bookmarks } from "@db/schema";
import { z } from "zod";

export function registerRoutes(app: Express): Server {
  // Import bookmarks
  app.post("/api/bookmarks/import", async (req, res) => {
    try {
      console.log('[Import] Starting bookmark import process');
      const bookmarks = req.body;

      if (!Array.isArray(bookmarks)) {
        return res.status(400).json({ 
          message: "Invalid request body. Expected an array of bookmarks." 
        });
      }

      console.log(`[Import] Processing ${bookmarks.length} bookmarks`);
      const result = await BookmarkModel.bulkCreate(bookmarks);

      console.log(`[Import] Successfully imported ${result.length} bookmarks`);
      res.json({ 
        success: true, 
        count: result.length,
        message: `Successfully imported ${result.length} bookmarks` 
      });
    } catch (error) {
      console.error("[Import] Error importing bookmarks:", error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to import bookmarks",
        error: true
      });
    }
  });

  // Parse HTML bookmarks
  app.post("/api/bookmarks/parse-html", async (req, res) => {
    try {
      console.log('[Parse] Starting HTML bookmark parsing');
      const htmlContent = req.body;

      if (typeof htmlContent !== 'string') {
        return res.status(400).json({ 
          message: "Invalid request body. Expected HTML content as string." 
        });
      }

      const bookmarks = await parseHtmlBookmarks(htmlContent);
      console.log(`[Parse] Successfully parsed ${bookmarks.length} bookmarks`);
      res.json(bookmarks);
    } catch (error) {
      console.error("[Parse] Error parsing HTML bookmarks:", error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to parse HTML bookmarks",
        error: true
      });
    }
  });

  // Purge all bookmarks
  app.delete("/api/bookmarks/purge", async (req, res) => {
    try {
      const result = await BookmarkModel.purgeAll();
      res.json({ success: true, message: "All bookmarks purged successfully" });
    } catch (error) {
      console.error("Error purging bookmarks:", error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to purge bookmarks" 
      });
    }
  });

  // AI Analysis endpoint
  app.post("/api/bookmarks/analyze", async (req, res) => {
    try {
      const { url } = req.body;
      if (!url) {
        return res.status(400).json({ message: 'URL is required' });
      }

      console.log(`[Analysis] Analyzing URL: ${url}`);
      const analysis = await AIService.analyzeUrl(url);
      console.log(`[Analysis] Analysis complete:`, analysis);

      res.json(analysis);
    } catch (error) {
      console.error('[Analysis] Error analyzing URL:', error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : 'Failed to analyze URL',
        error: true 
      });
    }
  });

  // Reanalyze specific bookmark
  app.post("/api/bookmarks/:id/analyze", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ message: "Invalid bookmark ID" });
      }

      const bookmark = await BookmarkModel.findById(id);
      if (!bookmark) {
        return res.status(404).json({ message: "Bookmark not found" });
      }

      console.log(`[Analysis] Starting reanalysis for bookmark ${id}`);
      const result = await BookmarkModel.enrichBookmarkAnalysis(bookmark);

      if (!result) {
        throw new Error("Failed to reanalyze bookmark");
      }

      // Get the updated bookmark after analysis
      const updatedBookmark = await BookmarkModel.findById(id);
      if (!updatedBookmark) {
        throw new Error("Failed to fetch updated bookmark");
      }

      console.log(`[Analysis] Completed reanalysis for bookmark ${id}`);
      res.json(updatedBookmark);
    } catch (error) {
      console.error("Error reanalyzing bookmark:", error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to reanalyze bookmark" 
      });
    }
  });

  // Get enrichment count
  app.get("/api/bookmarks/enrich/count", async (req, res) => {
    try {
      console.log("[Enrichment] Getting enrichment count");
      const count = await BookmarkModel.getEnrichmentCount();
      console.log(`[Enrichment] Count: ${count} bookmarks need enrichment`);
      res.json(count);
    } catch (error) {
      console.error("[Enrichment] Failed to get enrichment count:", error);
      res.status(500).json({ message: "Failed to get enrichment count" });
    }
  });

  // Start enrichment process
  app.post("/api/bookmarks/enrich", async (req, res) => {
    try {
      console.log("[Enrichment] Starting enrichment process");
      const count = await BookmarkModel.getEnrichmentCount();
      console.log(`[Enrichment] Found ${count} bookmarks to enrich`);

      if (count === 0) {
        return res.json({ message: "No bookmarks to enrich", count: 0 });
      }

      const result = await BookmarkModel.enrichAllBookmarks();
      console.log(`[Enrichment] Process started: ${result}`);

      if (result) {
        res.json({ message: "Enrichment process started successfully", count });
      } else {
        console.error("[Enrichment] Failed to start enrichment process");
        res.status(500).json({ message: "Failed to start enrichment process" });
      }
    } catch (error) {
      console.error("[Enrichment] Error starting enrichment:", error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to start enrichment process" 
      });
    }
  });

  // Get enrichment status
  app.get("/api/bookmarks/enrich/status", async (req, res) => {
    try {
      console.log("[Enrichment] Checking enrichment status");
      const [processedCount, remainingCount, totalCount] = await Promise.all([
        BookmarkModel.getProcessedCount(),
        BookmarkModel.getEnrichmentCount(),
        BookmarkModel.getTotalBookmarkCount()
      ]);

      console.log(`[Enrichment] Status: Processed=${processedCount}, Remaining=${remainingCount}, Total=${totalCount}`);

      // Ensure we don't exceed 100%
      const status = remainingCount === 0 ? "completed" : "processing";

      res.json({
        processedCount: Math.min(processedCount, totalCount),
        totalCount,
        status
      });
    } catch (error) {
      console.error("[Enrichment] Failed to get enrichment status:", error);
      res.status(500).json({ message: "Failed to get enrichment status" });
    }
  });

  // Create new bookmark
  app.post("/api/bookmarks", async (req, res) => {
    try {
      const result = await BookmarkModel.create(req.body);
      res.json(result);
    } catch (error) {
      console.error("Error creating bookmark:", error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to create bookmark" 
      });
    }
  });

  // Update bookmark by ID
  app.put("/api/bookmarks/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ message: "Invalid bookmark ID" });
      }

      console.log(`[Update] Updating bookmark ${id}:`, req.body);
      const result = await BookmarkModel.update(id, req.body);
      res.json(result);
    } catch (error) {
      console.error("Error updating bookmark:", error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to update bookmark" 
      });
    }
  });

  // Delete bookmark by ID
  app.delete("/api/bookmarks/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      if (isNaN(id)) {
        return res.status(400).json({ message: "Invalid bookmark ID" });
      }

      const result = await BookmarkModel.delete(id);
      if (!result) {
        return res.status(404).json({ message: "Bookmark not found" });
      }
      res.json({ success: true });
    } catch (error) {
      console.error("Error deleting bookmark:", error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to delete bookmark" 
      });
    }
  });

  // Get all bookmarks
  app.get("/api/bookmarks", async (req, res) => {
    try {
      const bookmarks = await BookmarkModel.findAll();
      res.json(bookmarks);
    } catch (error) {
      console.error("Failed to fetch bookmarks:", error);
      res.status(500).json({ 
        message: error instanceof Error ? error.message : "Failed to fetch bookmarks" 
      });
    }
  });

  app.get("/api/bookmarks/health", async (req, res) => {
    try {
      const bookmarks = await BookmarkModel.findAll();
      const total = bookmarks.length;
      const processed = bookmarks.filter(b => b.analysis?.status === 'success').length;
      const healthy = bookmarks.filter(b => 
        b.analysis?.status === 'success' && 
        b.analysis?.contentQuality?.overallScore >= 0.6
      ).length;
      const failed = bookmarks.filter(b => b.analysis?.status === 'error').length;
      const unanalyzed = bookmarks.filter(b => !b.analysis).length;
      const lowQuality = processed - healthy;
      
      res.json({
        total,
        healthy,
        processed,
        failed,
        unanalyzed,
        lowQuality,
        percentage: total > 0 ? Math.round((healthy / total) * 100) : 0
      });
    } catch (error) {
      console.error("Failed to get bookmark health:", error);
      res.status(500).json({ message: "Failed to get bookmark health status" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}