import { Client } from "@replit/database";
import { Bookmark, CreateBookmarkDto, UpdateBookmarkDto } from "../types/bookmark";

const db = new Client();

export const BookmarkService = {
  async getAll(): Promise<Bookmark[]> {
    const bookmarks = await db.list();
    return Promise.all(
      bookmarks
        .filter((key) => key.startsWith("bookmark:"))
        .map((key) => db.get(key))
    );
  },

  async getById(id: string): Promise<Bookmark | null> {
    return db.get(`bookmark:${id}`);
  },

  async create(data: CreateBookmarkDto): Promise<Bookmark> {
    const id = crypto.randomUUID();
    const bookmark: Bookmark = {
      id,
      ...data,
      userId: "system", // TODO: Replace with actual user ID
      dateAdded: new Date(),
      tags: data.tags || [],
      collections: data.collections || [],
    };
    await db.set(`bookmark:${id}`, bookmark);
    return bookmark;
  },

  async update(id: string, data: UpdateBookmarkDto): Promise<Bookmark | null> {
    const bookmark = await this.getById(id);
    if (!bookmark) return null;

    const updated: Bookmark = {
      ...bookmark,
      ...data,
    };
    await db.set(`bookmark:${id}`, updated);
    return updated;
  },

  async delete(id: string): Promise<boolean> {
    const bookmark = await this.getById(id);
    if (!bookmark) return false;
    await db.delete(`bookmark:${id}`);
    return true;
  },
};
