import fetch from 'node-fetch';
import Bottleneck from 'bottleneck';

export interface ZyteResponse {
    url: string;
    httpResponseBody: string;
    httpResponseHeaders: Record<string, string>;
    statusCode: number;
    content?: {
        title?: string;
        description?: string;
        text?: string;
    };
}

export interface ScrapeOptions {
    batchSize?: number;
    maxConcurrent?: number;
}

export class ZyteService {
    private static readonly MAX_RETRIES = 3;
    private static readonly API_ENDPOINT = 'https://api.zyte.com/v1/extract';
    private static readonly API_KEY = process.env.ZYTE_API_KEY;

    private static limiter = new Bottleneck({
        maxConcurrent: 5,
        minTime: 200
    });

    private static async scrapeUrl(url: string): Promise<ZyteResponse> {
        if (!this.API_KEY) {
            throw new Error('ZYTE_API_KEY environment variable is not set');
        }

        const response = await fetch(this.API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Basic ${Buffer.from(this.API_KEY + ':').toString('base64')}`
            },
            body: JSON.stringify({
                url,
                httpResponseBody: true,
                browserHtml: true
            })
        });

        if (response.status < 200 || response.status >= 300) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json() as ZyteResponse;
        if (!this.isValidResponse(data)) {
            throw new Error('Invalid response format from Zyte API');
        }

        return data;
    }

    private static async scrapeWithRetry(url: string): Promise<ZyteResponse | null> {
        for (let attempt = 0; attempt < this.MAX_RETRIES; attempt++) {
            try {
                return await this.limiter.schedule(() => this.scrapeUrl(url));
            } catch (error) {
                const isLastAttempt = attempt === this.MAX_RETRIES - 1;
                if (isLastAttempt) {
                    console.error(`Failed to scrape ${url} after ${this.MAX_RETRIES} attempts:`, error);
                    return null;
                }
                await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
            }
        }
        return null;
    }

    private static isValidResponse(data: any): data is ZyteResponse {
        return (
            typeof data === 'object' &&
            data !== null &&
            typeof data.url === 'string' &&
            typeof data.httpResponseBody === 'string' &&
            typeof data.httpResponseHeaders === 'object' &&
            typeof data.statusCode === 'number'
        );
    }

    static async scrapeBatch(urls: string[], options: ScrapeOptions = {}): Promise<Map<string, ZyteResponse>> {
        if (!this.API_KEY) {
            return new Map();
        }

        const { batchSize = 10, maxConcurrent = 5 } = options;
        const results = new Map<string, ZyteResponse>();

        // Process URLs in batches
        for (let i = 0; i < urls.length; i += batchSize) {
            const batch = urls.slice(i, i + batchSize);
            const batchResults = await Promise.all(
                batch.map(url => this.scrapeWithRetry(url))
            );

            // Store successful results
            batchResults.forEach((result, index) => {
                if (result) {
                    results.set(batch[index], result);
                }
            });
        }

        return results;
    }
} 