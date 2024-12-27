import type { Express } from "express";
import { createServer, type Server } from "http";
import { BookmarkModel } from "./models/bookmark";
import { insertBookmarkSchema } from "@db/schema";
import { z } from "zod";

// Schema for validating bookmark import data
const importBookmarkSchema = z.object({
  url: z.string().url(),
  title: z.string(),
  description: z.string().optional(),
  tags: z.array(z.string()).optional().default([]),
  collections: z.array(z.string()).optional().default([]),
}).array();

export function registerRoutes(app: Express): Server {
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
      const validatedData = insertBookmarkSchema.omit({ id: true, dateAdded: true }).parse(req.body);
      const bookmark = await BookmarkModel.create({
        ...validatedData,
        tags: validatedData.tags || [],
        collections: validatedData.collections || [],
      });
      res.status(201).json(bookmark);
    } catch (error) {
      console.error("Failed to create bookmark:", error);
      res.status(500).json({ message: "Failed to create bookmark" });
    }
  });

  app.put("/api/bookmarks/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id, 10);
      if (isNaN(id)) {
        return res.status(400).json({ message: "Invalid bookmark ID" });
      }

      const validatedData = insertBookmarkSchema.partial().omit({ id: true }).parse(req.body);
      const bookmark = await BookmarkModel.update(id, {
        ...validatedData,
        tags: validatedData.tags || undefined,
        collections: validatedData.collections || undefined,
      });
      if (!bookmark) {
        return res.status(404).json({ message: "Bookmark not found" });
      }
      res.json(bookmark);
    } catch (error) {
      console.error("Failed to update bookmark:", error);
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

  // Bulk import endpoint
  app.post("/api/bookmarks/import", async (req, res) => {
    try {
      // Validate the incoming data
      const bookmarks = importBookmarkSchema.parse(req.body);

      // Check if the request is too large
      if (bookmarks.length > 15000) {
        return res.status(400).json({
          message: "Import size too large. Maximum 15,000 bookmarks allowed per import."
        });
      }

      // Process the import
      const imported = await BookmarkModel.bulkCreate(bookmarks);

      res.status(201).json({
        message: `Successfully imported ${imported.length} bookmarks`,
        count: imported.length
      });
    } catch (error) {
      console.error("Failed to import bookmarks:", error);
      if (error instanceof z.ZodError) {
        return res.status(400).json({
          message: "Invalid bookmark data format",
          errors: error.errors
        });
      }
      res.status(500).json({ message: "Failed to import bookmarks" });
    }
  });

  const httpServer = createServer(app);
  return httpServer;
}