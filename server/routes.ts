
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
