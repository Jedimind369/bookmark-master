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
      const validatedData = await insertBookmarkSchema.omit({ id: true, dateAdded: true }).parseAsync(req.body);
      const bookmark = await BookmarkModel.create(validatedData);
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

  app.put("/api/bookmarks/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id, 10);
      if (isNaN(id)) {
        return res.status(400).json({ message: "Invalid bookmark ID" });
      }

      const validatedData = await insertBookmarkSchema.partial().omit({ id: true }).parseAsync(req.body);
      const bookmark = await BookmarkModel.update(id, validatedData);

      if (!bookmark) {
        return res.status(404).json({ message: "Bookmark not found" });
      }

      res.json(bookmark);
    } catch (error) {
      console.error("Failed to update bookmark:", error);
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          message: "Invalid bookmark data",
          errors: error.errors
        });
      }
      res.status(500).json({ message: "Failed to update bookmark" });
    }
  });

  app.delete("/api/bookmarks/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id, 10);
      if (isNaN(id)) {
        return res.status(400).json({ message: "Invalid bookmark ID" });
      }

      const success = await BookmarkModel.delete(id);
      if (!success) {
        return res.status(404).json({ message: "Bookmark not found" });
      }
      res.status(204).send();
    } catch (error) {
      console.error("Failed to delete bookmark:", error);
      res.status(500).json({ message: "Failed to delete bookmark" });
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

  // Endpoint to manually enrich bookmarks with comprehensive analysis
  app.post("/api/bookmarks/enrich", async (req, res) => {
    try {
      // Get count of bookmarks that need enrichment
      const count = await BookmarkModel.getEnrichmentCount();

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

  // HTML Bookmark parsing endpoint
  app.post("/api/bookmarks/parse-html", async (req, res) => {
    try {
      // Get raw HTML content from request body
      const htmlContent = req.body;
      if (typeof htmlContent !== 'string') {
        return res.status(400).json({ message: "Invalid HTML content" });
      }

      // Parse the HTML bookmarks
      const bookmarks = parseHtmlBookmarks(htmlContent);
      res.json(bookmarks);
    } catch (error) {
      console.error("Failed to parse HTML bookmarks:", error);
      res.status(500).json({ message: "Failed to parse HTML bookmarks" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}