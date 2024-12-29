import fetch from 'node-fetch';
import Bottleneck from 'bottleneck';
import { EventEmitter } from 'events';

if (!process.env.ZYTE_API_KEY) {
  throw new Error("ZYTE_API_KEY is not set");
}

// Configure rate limiter for Zyte API
const limiter = new Bottleneck({
  maxConcurrent: 10, // Maximum number of concurrent requests
  minTime: 100, // Minimum time between requests (ms)
  reservoir: 100, // Number of requests allowed per reservoirRefreshAmount
  reservoirRefreshAmount: 100, // How many requests to add to reservoir
  reservoirRefreshInterval: 60 * 1000, // Refresh interval in milliseconds (1 minute)
});

export interface ZyteResponse {
  url: string;
  httpResponseBody: string;
  httpResponseHeaders: Record<string, string>;
  statusCode: number;
  content?: {
    title?: string;
    description?: string;
    text?: string;
    mainImage?: string;
    author?: string;
    publishedDate?: string;
  };
}

export interface ScrapeProgress {
  total: number;
  completed: number;
  failed: number;
  inProgress: number;
  errors: Array<{ url: string; error: string }>;
  startTime: Date;
  estimatedTimeRemaining?: number;
}

export interface ScrapeOptions {
  batchSize?: number;
  maxConcurrent?: number;
  onProgress?: (progress: ScrapeProgress) => void;
}

export class ZyteService {
  private static readonly MAX_RETRIES = 3;
  private static readonly INITIAL_RETRY_DELAY = 1000;
  private static readonly API_ENDPOINT = 'https://api.zyte.com/v1/extract';
  private static readonly API_KEY = process.env.ZYTE_API_KEY;
  
  private static limiter = limiter;
  private static progressEmitter = new EventEmitter();

  private static async delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private static async scrapeWithRetry(url: string): Promise<ZyteResponse> {
    let lastError: Error | null = null;

    for (let i = 0; i < this.MAX_RETRIES; i++) {
      try {
        const response = await this.limiter.schedule(() => 
          fetch(this.API_ENDPOINT, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Basic ${Buffer.from(this.API_KEY + ':').toString('base64')}`
            },
            body: JSON.stringify({
              url,
              httpResponseBody: true,
              browserHtml: true,
              javascript: true,
              customScripts: true
            })
          })
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json() as ZyteResponse;
        if (!this.isValidZyteResponse(data)) {
          throw new Error('Invalid response format from Zyte API');
        }
        return data;
      } catch (error) {
        lastError = error as Error;
        const delay = this.INITIAL_RETRY_DELAY * Math.pow(2, i);
        await this.delay(delay);
      }
    }

    throw lastError || new Error(`Failed to scrape ${url} after multiple retries`);
  }

  private static isValidZyteResponse(data: any): data is ZyteResponse {
    return (
      typeof data === 'object' &&
      data !== null &&
      typeof data.url === 'string' &&
      typeof data.httpResponseBody === 'string' &&
      typeof data.httpResponseHeaders === 'object' &&
      typeof data.statusCode === 'number'
    );
  }

  static async scrapeBatch(
    urls: string[],
    options: ScrapeOptions = {}
  ): Promise<Map<string, ZyteResponse>> {
    const {
      batchSize = 50,
      maxConcurrent = 10,
      onProgress
    } = options;

    const results = new Map<string, ZyteResponse>();
    const progress: ScrapeProgress = {
      total: urls.length,
      completed: 0,
      failed: 0,
      inProgress: 0,
      errors: [],
      startTime: new Date()
    };

    // Process URLs in batches
    for (let i = 0; i < urls.length; i += batchSize) {
      const batchUrls = urls.slice(i, i + batchSize);
      const batchPromises = batchUrls.map(async (url) => {
        progress.inProgress++;
        this.updateProgress(progress, onProgress);

        try {
          const result = await this.scrapeWithRetry(url);
          results.set(url, result);
          progress.completed++;
        } catch (error) {
          progress.failed++;
          progress.errors.push({
            url,
            error: error instanceof Error ? error.message : 'Unknown error'
          });
          console.error(`[Batch] Failed to scrape ${url}:`, error);
        } finally {
          progress.inProgress--;
          this.updateEstimatedTimeRemaining(progress);
          this.updateProgress(progress, onProgress);
        }
      });

      // Process batch with concurrency limit
      await Promise.all(
        batchPromises.map((promise) => this.limiter.schedule(() => promise))
      );

      // Log batch completion
      console.log(`[Batch] Completed batch ${i / batchSize + 1} of ${Math.ceil(urls.length / batchSize)}`);
      console.log(`[Batch] Progress: ${progress.completed}/${progress.total} (${progress.failed} failed)`);
    }

    return results;
  }

  private static updateEstimatedTimeRemaining(progress: ScrapeProgress): void {
    const elapsed = Date.now() - progress.startTime.getTime();
    const completedCount = progress.completed + progress.failed;
    if (completedCount === 0) return;

    const averageTimePerUrl = elapsed / completedCount;
    const remainingUrls = progress.total - completedCount;
    progress.estimatedTimeRemaining = averageTimePerUrl * remainingUrls;
  }

  private static updateProgress(
    progress: ScrapeProgress,
    onProgress?: (progress: ScrapeProgress) => void
  ): void {
    if (onProgress) {
      onProgress(progress);
    }
    this.progressEmitter.emit('progress', progress);
  }

  static onProgress(callback: (progress: ScrapeProgress) => void): void {
    this.progressEmitter.on('progress', callback);
  }

  static offProgress(callback: (progress: ScrapeProgress) => void): void {
    this.progressEmitter.off('progress', callback);
  }
} 