import { IBookmarkService, IScrapingService, IMetricsService, ValidationResult, Bookmark, EnrichedBookmark } from '../../interfaces/services';
import { UrlValidator } from './validators/BookmarkValidator';
import { performanceMonitor } from '../../utils/monitoring';
import { logger } from '../../utils/logger';

export class BookmarkService implements IBookmarkService {
    constructor(
        private scraper: IScrapingService,
        private metrics: IMetricsService
    ) {}

    async validate(url: string): Promise<ValidationResult> {
        const startTime = Date.now();
        try {
            const validator = new UrlValidator();
            const result = await validator.validate({ url });
            
            this.metrics.track({
                operation: 'validate_bookmark',
                duration: Date.now() - startTime
            });
            
            return result;
        } catch (error) {
            this.metrics.track({
                operation: 'validate_bookmark',
                error: true
            });
            logger.error('Bookmark validation failed:', error);
            throw error;
        }
    }

    async enrich(bookmark: Bookmark): Promise<EnrichedBookmark> {
        const startTime = Date.now();
        try {
            // First validate the bookmark
            const validationResult = await this.validate(bookmark.url);
            if (!validationResult.isValid) {
                throw new Error(`Invalid bookmark: ${validationResult.errors.join(', ')}`);
            }

            // Scrape content
            const scrapedContent = await this.scraper.scrape(bookmark.url);
            
            // Enrich the bookmark with scraped content
            const enrichedBookmark: EnrichedBookmark = {
                ...bookmark,
                title: bookmark.title || scrapedContent.title,
                metadata: scrapedContent.metadata,
                analysis: {
                    contentQuality: {
                        relevance: 0.8,
                        informativeness: 0.8,
                        credibility: 0.8
                    },
                    mainTopics: []
                }
            };

            this.metrics.track({
                operation: 'enrich_bookmark',
                duration: Date.now() - startTime
            });

            return enrichedBookmark;
        } catch (error) {
            this.metrics.track({
                operation: 'enrich_bookmark',
                error: true
            });
            logger.error('Bookmark enrichment failed:', error);
            throw error;
        }
    }

    async save(bookmark: Bookmark): Promise<void> {
        const startTime = Date.now();
        try {
            // TODO: Implement database save logic
            performanceMonitor.trackDatabaseOperation('save_bookmark', Date.now() - startTime);
            
            this.metrics.track({
                operation: 'save_bookmark',
                duration: Date.now() - startTime
            });
        } catch (error) {
            this.metrics.track({
                operation: 'save_bookmark',
                error: true
            });
            logger.error('Bookmark save failed:', error);
            throw error;
        }
    }
} 