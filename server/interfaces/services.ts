// Core service interfaces for Bookmark Master

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

export interface Bookmark {
  url: string;
  title?: string;
  description?: string;
  tags?: string[];
}

export interface EnrichedBookmark extends Bookmark {
  metadata?: {
    author?: string;
    publishDate?: string;
    lastModified?: string;
    mainImage?: string;
  };
  analysis?: {
    contentQuality?: {
      relevance: number;
      informativeness: number;
      credibility: number;
    };
    mainTopics?: string[];
  };
}

export interface ScrapedContent {
  url: string;
  title: string;
  content: string;
  metadata?: {
    author?: string;
    publishDate?: string;
    lastModified?: string;
    mainImage?: string;
  };
}

export interface Metric {
  operation: string;
  duration?: number;
  error?: boolean;
}

export interface PerformanceStats {
  requestCount: number;
  averageResponseTime: number;
  errorRate: number;
  memoryUsage: number;
}

export interface IBookmarkService {
  validate(url: string): Promise<ValidationResult>;
  enrich(bookmark: Bookmark): Promise<EnrichedBookmark>;
  save(bookmark: Bookmark): Promise<void>;
}

export interface IScrapingService {
  scrape(url: string): Promise<ScrapedContent>;
  validateContent(content: ScrapedContent): ValidationResult;
}

export interface IMetricsService {
  track(metric: Metric): void;
  getStats(): PerformanceStats;
} 