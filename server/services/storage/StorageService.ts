import { injectable } from 'tsyringe';
import type { Bookmark } from '../../interfaces/services';
import { db } from '../../../db';
import { BaseService } from '../base/BaseService';
import { bookmarks } from '../../../db/schema';
import { eq } from 'drizzle-orm';
import { logger } from '../../utils/logger';

export interface IStorageService {
    save(bookmark: Bookmark): Promise<void>;
    findByUrl(url: string): Promise<Bookmark | null>;
    delete(url: string): Promise<void>;
}

@injectable()
export class StorageService extends BaseService implements IStorageService {
    async save(bookmark: Bookmark): Promise<void> {
        return this.executeOperation('save_bookmark', async () => {
            try {
                await db.insert(bookmarks).values({
                    url: bookmark.url,
                    title: bookmark.title || '',
                    description: bookmark.description || '',
                    tags: bookmark.tags || [],
                    userId: 1, // TODO: Get from auth context
                    dateAdded: bookmark.createdAt || new Date(),
                    dateModified: new Date(),
                    isArchived: false,
                    collections: [],
                    lastValidated: new Date(),
                    validationAttempts: 0,
                    analysis: null
                });
            } catch (error) {
                logger.error('Failed to save bookmark:', {
                    url: bookmark.url,
                    error: error instanceof Error ? error.message : 'Unknown error'
                });
                throw error;
            }
        });
    }

    async findByUrl(url: string): Promise<Bookmark | null> {
        return this.executeOperation('find_bookmark', async () => {
            try {
                const result = await db.select().from(bookmarks).where(eq(bookmarks.url, url));
                if (!result.length) return null;

                const bookmark = result[0];
                return {
                    url: bookmark.url,
                    title: bookmark.title,
                    description: bookmark.description || undefined,
                    tags: bookmark.tags || [],
                    createdAt: bookmark.dateAdded || new Date(),
                    updatedAt: bookmark.dateModified || new Date()
                };
            } catch (error) {
                logger.error('Failed to find bookmark:', {
                    url,
                    error: error instanceof Error ? error.message : 'Unknown error'
                });
                throw error;
            }
        });
    }

    async delete(url: string): Promise<void> {
        return this.executeOperation('delete_bookmark', async () => {
            try {
                await db.delete(bookmarks).where(eq(bookmarks.url, url));
            } catch (error) {
                logger.error('Failed to delete bookmark:', {
                    url,
                    error: error instanceof Error ? error.message : 'Unknown error'
                });
                throw error;
            }
        });
    }
} 