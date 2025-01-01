import { BookmarkService } from '../../services/bookmark/BookmarkService';
import { createMockScraper, createMockMetrics } from '../utils/mocks';
import type { IScrapingService, IMetricsService } from '../../interfaces/services';

describe('BookmarkService', () => {
    let bookmarkService: BookmarkService;
    let mockScraper: jest.Mocked<IScrapingService>;
    let mockMetrics: jest.Mocked<IMetricsService>;

    beforeEach(() => {
        mockScraper = createMockScraper();
        mockMetrics = createMockMetrics();
        bookmarkService = new BookmarkService(mockScraper, mockMetrics);
    });

    describe('validate', () => {
        test('should return valid result for correct URL', async () => {
            const result = await bookmarkService.validate('https://example.com');
            expect(result.isValid).toBe(true);
            expect(result.errors).toHaveLength(0);
        });

        test('should return invalid result for incorrect URL', async () => {
            const result = await bookmarkService.validate('not-a-url');
            expect(result.isValid).toBe(false);
            expect(result.errors).toContain('Invalid URL format');
        });

        test('should track metrics', async () => {
            await bookmarkService.validate('https://example.com');
            expect(mockMetrics.track).toHaveBeenCalledWith(
                expect.objectContaining({
                    operation: 'validate_bookmark'
                })
            );
        });
    });

    describe('enrich', () => {
        test('should enrich valid bookmark', async () => {
            const bookmark = {
                url: 'https://example.com',
                title: 'Test'
            };

            const enriched = await bookmarkService.enrich(bookmark);
            
            expect(enriched).toMatchObject({
                url: bookmark.url,
                title: bookmark.title,
                metadata: expect.any(Object),
                analysis: expect.objectContaining({
                    contentQuality: expect.any(Object)
                })
            });
        });

        test('should throw error for invalid bookmark', async () => {
            const bookmark = {
                url: 'invalid-url',
                title: 'Test'
            };

            await expect(bookmarkService.enrich(bookmark)).rejects.toThrow();
        });

        test('should use scraper service', async () => {
            const bookmark = {
                url: 'https://example.com'
            };

            await bookmarkService.enrich(bookmark);
            expect(mockScraper.scrape).toHaveBeenCalledWith(bookmark.url);
        });
    });

    describe('save', () => {
        test('should validate before saving', async () => {
            const bookmark = {
                url: 'https://example.com',
                title: 'Test'
            };

            await bookmarkService.save(bookmark);
            expect(mockMetrics.track).toHaveBeenCalledWith(
                expect.objectContaining({
                    operation: 'save_bookmark'
                })
            );
        });

        test('should throw error for invalid bookmark', async () => {
            const bookmark = {
                url: 'invalid-url',
                title: 'Test'
            };

            await expect(bookmarkService.save(bookmark)).rejects.toThrow();
        });
    });
}); 