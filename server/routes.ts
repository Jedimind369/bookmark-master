import type { Express } from "express";
import { createServer, type Server } from "http";
import { BookmarkModel } from "./models/bookmark";
import { AIService } from "./services/aiService";
import { insertBookmarkSchema } from "@db/schema";
import { parseHtmlBookmarks } from "./utils/bookmarkParser";
import { z } from "zod";

export function registerRoutes(app: Express): Server {
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
      const count = await BookmarkModel.getEnrichmentCount();
      res.json(count);
    } catch (error) {
      console.error("Failed to get enrichment count:", error);
      res.status(500).json({ message: "Failed to get enrichment count" });
    }
  });

  // Start enrichment process
  app.post("/api/bookmarks/enrich", async (req, res) => {
    try {
      console.log("[Enrichment] Starting enrichment process");
      const result = await BookmarkModel.enrichAllBookmarks();
      if (result) {
        res.json({ message: "Enrichment process started successfully", count: result });
      } else {
        res.status(500).json({ message: "Failed to start enrichment process" });
      }
    } catch (error) {
      console.error("Error starting enrichment:", error);
      res.status(500).json({ message: "Failed to start enrichment process" });
    }
  });

  // Get enrichment status
  app.get("/api/bookmarks/enrich/status", async (req, res) => {
    try {
      const processedCount = await BookmarkModel.getProcessedCount();
      const totalCount = await BookmarkModel.getEnrichmentCount();

      res.json({
        processedCount,
        totalCount,
        status: "processing",
      });
    } catch (error) {
      console.error("Failed to get enrichment status:", error);
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
      res.status(500).json({ message: "Failed to create bookmark" });
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

  // Get all bookmarks
  app.get("/api/bookmarks", async (req, res) => {
    try {
      const bookmarks = await BookmarkModel.findAll();
      res.json(bookmarks);
    } catch (error) {
      console.error("Failed to fetch bookmarks:", error);
      res.status(500).json({ message: "Failed to fetch bookmarks" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}