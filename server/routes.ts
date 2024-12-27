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
        return res.status(400).json({ error: 'URL is required' });
      }
      const analysis = await AIService.analyzeUrl(url);
      res.json(analysis);
    } catch (error) {
      console.error('Error analyzing URL:', error);
      res.status(500).json({ error: 'Failed to analyze URL' });
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
        res.json({ message: "Enrichment process started successfully" });
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

  // Rest of your routes...
  app.get("/api/bookmarks", async (req, res) => {
    try {
      const bookmarks = await BookmarkModel.findAll();
      res.json(bookmarks);
    } catch (error) {
      console.error("Failed to fetch bookmarks:", error);
      res.status(500).json({ message: "Failed to fetch bookmarks" });
    }
  });

  // Add other existing routes here...

  const httpServer = createServer(app);
  return httpServer;
}