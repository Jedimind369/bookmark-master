import { pgTable, text, serial, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").unique().notNull(),
  password: text("password").notNull(),
});

// Define the analysis status type
export type AnalysisStatus = 'success' | 'error' | 'invalid_url' | 'rate_limited' | 'unreachable' | 'system_error' | 'processing';

export const bookmarks = pgTable("bookmarks", {
  id: serial("id").primaryKey(),
  url: text("url").notNull(),
  title: text("title").notNull(),
  description: text("description"),
  tags: jsonb("tags").$type<string[]>().default([]),
  collections: jsonb("collections").$type<string[]>().default([]),
  dateAdded: timestamp("date_added").defaultNow(),
  dateModified: timestamp("date_modified"),
  analysis: jsonb("analysis").$type<{
    status?: AnalysisStatus;
    lastUpdated?: string;
    summary?: string;
    error?: string;
    retryable?: boolean;
    tags?: string[];
    contentQuality?: {
      relevance: number;
      informativeness: number;
      credibility: number;
      overallScore: number;
    };
    mainTopics?: string[];
    recommendations?: {
      improvedTitle?: string;
      improvedDescription?: string;
      suggestedTags?: string[];
    };
  }>(),
});

// User schemas
export const insertUserSchema = createInsertSchema(users);
export const selectUserSchema = createSelectSchema(users);
export type InsertUser = typeof users.$inferInsert;
export type SelectUser = typeof users.$inferSelect;

// Bookmark schemas
export const insertBookmarkSchema = createInsertSchema(bookmarks);
export const selectBookmarkSchema = createSelectSchema(bookmarks);
export type InsertBookmark = typeof bookmarks.$inferInsert;
export type SelectBookmark = typeof bookmarks.$inferSelect;