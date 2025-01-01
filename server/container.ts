import { container } from 'tsyringe';
import { BookmarkService } from './services/bookmark/BookmarkService';
import { MetricsService } from './services/metrics/MetricsService';
import { ZyteScrapingService } from './services/scraping/ScrapingService';

// Register services
container.register('IBookmarkService', {
    useClass: BookmarkService
});

container.register('IMetricsService', {
    useClass: MetricsService
});

container.register('IScrapingService', {
    useClass: ZyteScrapingService
});

export { container }; 