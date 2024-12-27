import type { Express } from "express";
import { createServer, type Server } from "http";
import { BookmarkModel } from "./models/bookmark";
import { insertBookmarkSchema } from "@db/schema";

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
      const bookmark = await BookmarkModel.create(validatedData);
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
      const bookmark = await BookmarkModel.update(id, validatedData);
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

  const httpServer = createServer(app);
  return httpServer;
}