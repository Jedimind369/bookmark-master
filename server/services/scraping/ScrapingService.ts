import { IScrapingService, ScrapedContent, ValidationResult } from '../../interfaces/services';
import Bottleneck from 'bottleneck';
import { logger } from '../../utils/logger';
import { performanceConfig } from '../../config/performance';
import * as cheerio from 'cheerio';

export class ZyteScrapingService implements IScrapingService {
    private limiter: Bottleneck;

    constructor() {
        this.limiter = new Bottleneck({
            maxConcurrent: performanceConfig.scraping.maxConcurrent || 5,
            minTime: performanceConfig.scraping.minTime || 200,
            reservoir: performanceConfig.scraping.reservoir || 50,
            reservoirRefreshAmount: performanceConfig.scraping.reservoir || 50,
            reservoirRefreshInterval: performanceConfig.scraping.windowMs || 60000
        });
    }

    async scrape(url: string): Promise<ScrapedContent> {
        return this.limiter.schedule(async () => {
            const startTime = Date.now();
            const controller = new AbortController();
            const timeout = setTimeout(() => {
                controller.abort();
            }, performanceConfig.scraping.timeout || 10000);

            try {
                const response = await fetch(url, {
                    headers: {
                        'Accept': 'text/html,application/xhtml+xml',
                        'User-Agent': 'Mozilla/5.0 (compatible; BookmarkAnalyzer/1.0)'
                    },
                    signal: controller.signal
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const html = await response.text();
                const $ = cheerio.load(html);

                // Clean up unnecessary elements
                $('script, style, iframe, noscript').remove();

                const title = $('meta[property="og:title"]').attr('content') ||
                            $('title').text() ||
                            url.split('/').pop() ||
                            'Untitled';

                const content = $('article, main, .content')
                    .map((_, el) => $(el).text())
                    .get()
                    .join(' ')
                    .replace(/\s+/g, ' ')
                    .trim();

                const scrapedContent: ScrapedContent = {
                    url,
                    title: title.slice(0, 200),
                    content: content.slice(0, 5000),
                    metadata: {
                        author: $('meta[name="author"]').attr('content')?.slice(0, 100),
                        publishDate: $('meta[property="article:published_time"]').attr('content'),
                        lastModified: $('meta[property="article:modified_time"]').attr('content'),
                        mainImage: $('meta[property="og:image"]').attr('content')
                    }
                };

                logger.debug('Content scraped successfully', {
                    url,
                    duration: Date.now() - startTime
                });

                return scrapedContent;
            } catch (error) {
                logger.error('Failed to scrape content:', {
                    url,
                    error: error instanceof Error ? error.message : 'Unknown error',
                    duration: Date.now() - startTime
                });
                throw error;
            } finally {
                clearTimeout(timeout);
            }
        });
    }

    validateContent(content: ScrapedContent): ValidationResult {
        const errors: string[] = [];

        if (!content.url) {
            errors.push('URL is required');
        }

        if (!content.title) {
            errors.push('Title is required');
        }

        if (!content.content || content.content.length < 50) {
            errors.push('Content is too short or missing');
        }

        // Validate metadata if present
        if (content.metadata) {
            if (content.metadata.publishDate && isNaN(Date.parse(content.metadata.publishDate))) {
                errors.push('Invalid publish date format');
            }
            if (content.metadata.lastModified && isNaN(Date.parse(content.metadata.lastModified))) {
                errors.push('Invalid last modified date format');
            }
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    }
} 