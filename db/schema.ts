import { pgTable, text, serial, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";
import type { AnalysisStatus, ContentQuality, VideoContent, BookmarkAnalysis } from "@shared/types/bookmark";

export const bookmarks = pgTable("bookmarks", {
  id: serial("id").primaryKey(),
  url: text("url").notNull(),
  title: text("title").notNull(),
  description: text("description"),
  tags: jsonb("tags").$type<string[]>().default([]),
  collections: jsonb("collections").$type<string[]>().default([]),
  dateAdded: timestamp("date_added").defaultNow(),
  dateModified: timestamp("date_modified"),
  analysis: jsonb("analysis").$type<BookmarkAnalysis>(),
  updateHistory: jsonb("update_history").$type<Array<{
    timestamp: string;
    status: AnalysisStatus;
    message?: string;
  }>>().default([]),
});

// Bookmark schemas
export const insertBookmarkSchema = createInsertSchema(bookmarks);
export const selectBookmarkSchema = createSelectSchema(bookmarks);
export type InsertBookmark = typeof bookmarks.$inferInsert;
export type SelectBookmark = typeof bookmarks.$inferSelect;

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").unique().notNull(),
  password: text("password").notNull(),
});

// User schemas
export const insertUserSchema = createInsertSchema(users);
export const selectUserSchema = createSelectSchema(users);
export type InsertUser = typeof users.$inferInsert;
export type SelectUser = typeof users.$inferSelect;