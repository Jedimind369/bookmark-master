import { pgTable, text, serial, timestamp, jsonb, integer, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { relations } from "drizzle-orm";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").unique().notNull(),
  password: text("password").notNull(),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at"),
});

// Enhanced analysis status type with more granular states
export type AnalysisStatus = 
  | 'pending'
  | 'processing'
  | 'success'
  | 'error'
  | 'invalid_url'
  | 'rate_limited'
  | 'unreachable'
  | 'system_error'
  | 'needs_revalidation';

export const bookmarks = pgTable("bookmarks", {
  id: serial("id").primaryKey(),
  url: text("url").notNull(),
  title: text("title").notNull(),
  description: text("description"),
  tags: jsonb("tags").$type<string[]>().default([]),
  collections: jsonb("collections").$type<string[]>().default([]),
  userId: integer("user_id").references(() => users.id).notNull(),
  dateAdded: timestamp("date_added").defaultNow(),
  dateModified: timestamp("date_modified"),
  isArchived: boolean("is_archived").default(false),
  lastValidated: timestamp("last_validated"),
  validationAttempts: integer("validation_attempts").default(0),
  analysis: jsonb("analysis").$type<{
    status?: AnalysisStatus;
    lastUpdated?: string;
    error?: string;
    retryable?: boolean;
    summary?: string;
    quality: {
      relevance: number;      // 0-1: How relevant the content is to the title/description
      informativeness: number; // 0-1: How informative/detailed the content is
      credibility: number;    // 0-1: Source credibility and content authenticity
      accessibility: number;  // 0-1: Content accessibility (load time, availability)
      overallScore: number;   // 0-1: Weighted average of all scores
    };
    tags?: string[];
    mainTopics?: string[];
    metadata: {
      author?: string;
      publishDate?: string;
      lastModified?: string;
      mainImage?: string;
      wordCount?: number;
      readingTime?: number;
      domainAuthority?: number;
      language?: string;
      encoding?: string;
      contentType?: string;
      statusCode?: number;
      responseTime?: number;
      certificateValid?: boolean;
    };
    recommendations?: {
      improvedTitle?: string;
      improvedDescription?: string;
      suggestedTags?: string[];
      suggestedCollections?: string[];
      qualityImprovements?: string[];
    };
  }>(),
});

// Define relations
export const bookmarksRelations = relations(bookmarks, ({ one }) => ({
  user: one(users, {
    fields: [bookmarks.userId],
    references: [users.id],
  }),
}));

export const usersRelations = relations(users, ({ many }) => ({
  bookmarks: many(bookmarks),
}));

// Enhanced user schemas
export const insertUserSchema = createInsertSchema(users);
export const selectUserSchema = createSelectSchema(users);
export type InsertUser = typeof users.$inferInsert;
export type SelectUser = typeof users.$inferSelect;

// Enhanced bookmark schemas with validation
export const insertBookmarkSchema = createInsertSchema(bookmarks, {
  url: z.string().url("Invalid URL format").min(1, "URL is required"),
  title: z.string().min(1, "Title is required").max(200, "Title is too long"),
  description: z.string().max(1000, "Description is too long").optional(),
  tags: z.array(z.string()).max(20, "Too many tags").optional(),
  collections: z.array(z.string()).max(10, "Too many collections").optional(),
});

export const selectBookmarkSchema = createSelectSchema(bookmarks);
export type InsertBookmark = typeof bookmarks.$inferInsert;
export type SelectBookmark = typeof bookmarks.$inferSelect;