import { injectable, inject } from 'tsyringe';
import type { IBookmarkService, IScrapingService, IMetricsService, ValidationResult, Bookmark, EnrichedBookmark, ScrapedContent } from '../../interfaces/services';
import { UrlValidator } from './validators/BookmarkValidator';
import { BaseService } from '../base/BaseService';

@injectable()
export class BookmarkService extends BaseService implements IBookmarkService {
    constructor(
        @inject('IScrapingService') private scraper: IScrapingService,
        @inject('IMetricsService') private metrics: IMetricsService
    ) {
        super();
    }

    async validate(url: string): Promise<ValidationResult> {
        return this.executeOperation('validate_bookmark', async () => {
            const validator = new UrlValidator();
            return validator.validate({ url });
        });
    }

    async enrich(bookmark: Bookmark): Promise<EnrichedBookmark> {
        return this.executeOperation('enrich_bookmark', async () => {
            const validationResult = await this.validate(bookmark.url);
            if (!validationResult.isValid) {
                throw new Error(validationResult.errors.join(', '));
            }
            const scrapedContent = await this.scraper.scrape(bookmark.url);
            return this.enrichBookmark(bookmark, scrapedContent);
        });
    }

    async save(bookmark: Bookmark): Promise<void> {
        return this.executeOperation('save_bookmark', async () => {
            const validation = await this.validate(bookmark.url);
            if (!validation.isValid) {
                throw new Error(validation.errors.join(', '));
            }
            // TODO: Implement database save logic
            this.metrics.track({
                operation: 'save_bookmark',
                duration: Date.now()
            });
        });
    }

    private enrichBookmark(bookmark: Bookmark, scrapedContent: ScrapedContent): EnrichedBookmark {
        return {
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
    }
} 