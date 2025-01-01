import type { IScrapingService, IMetricsService, ScrapedContent, ValidationResult } from '../../interfaces/services';

export const createMockScraper = (): jest.Mocked<IScrapingService> => ({
    scrape: jest.fn().mockResolvedValue({
        url: 'https://example.com',
        title: 'Example Title',
        content: 'Example Content',
        metadata: {
            author: 'Test Author',
            publishDate: '2024-03-20'
        }
    } as ScrapedContent),
    validateContent: jest.fn().mockReturnValue({
        isValid: true,
        errors: []
    } as ValidationResult)
});

export const createMockMetrics = (): jest.Mocked<IMetricsService> => ({
    track: jest.fn(),
    getStats: jest.fn().mockReturnValue({
        requestCount: 0,
        averageResponseTime: 0,
        errorRate: 0,
        memoryUsage: 0
    })
}); 