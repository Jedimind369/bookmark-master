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
  userId: serial("user_id").references(() => users.id),
  dateAdded: timestamp("date_added").defaultNow(),
  dateModified: timestamp("date_modified"),
  updateHistory: jsonb("update_history").$type<Array<{
    timestamp: string;
    changes: Record<string, any>;
    previousState: Record<string, any>;
  }>>().default([]),
  analysis: jsonb("analysis").$type<{
    summary?: string;
    credibilityScore?: number;
    status?: AnalysisStatus;
    lastUpdated?: string;
    error?: string;
    retryable?: boolean;
    tags?: string[];
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