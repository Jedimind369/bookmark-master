// Set environment variables before importing ZyteService
process.env.ZYTE_API_KEY = 'test-api-key';

import { ZyteService } from '../services/zyteService.js';
import { jest, describe, test, expect, beforeEach } from '@jest/globals';
import { mockFetch, MockResponse } from './setup.js';

describe('ZyteService', () => {
    const validResponse = {
        url: 'https://example.com',
        httpResponseBody: '<html><body>Test content</body></html>',
        httpResponseHeaders: { 'content-type': 'text/html' },
        statusCode: 200,
        content: {
            title: 'Test Page',
            description: 'Test description',
            text: 'Test content'
        }
    };

    beforeEach(() => {
        mockFetch.mockClear();
        process.env.ZYTE_API_KEY = 'test-api-key';
    });

    describe('Basic Scraping', () => {
        test('should successfully scrape a URL', async () => {
            mockFetch.mockResolvedValueOnce(new MockResponse(JSON.stringify(validResponse), {
                status: 200,
                headers: { 'content-type': 'application/json' }
            }));

            const urls = ['https://example.com'];
            const results = await ZyteService.scrapeBatch(urls);

            expect(results.size).toBe(1);
            expect(results.get(urls[0])).toEqual(validResponse);
            expect(mockFetch).toHaveBeenCalledTimes(1);
        });

        test('should handle missing API key', async () => {
            delete process.env.ZYTE_API_KEY;

            const urls = ['https://example.com'];
            const results = await ZyteService.scrapeBatch(urls);

            expect(results.size).toBe(0);
            expect(mockFetch).not.toHaveBeenCalled();
        });
    });

    describe('Error Handling', () => {
        test('should retry on failure', async () => {
            mockFetch
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValueOnce(new MockResponse(JSON.stringify(validResponse), {
                    status: 200,
                    headers: { 'content-type': 'application/json' }
                }));

            const urls = ['https://example.com'];
            const results = await ZyteService.scrapeBatch(urls);

            expect(results.size).toBe(1);
            expect(mockFetch).toHaveBeenCalledTimes(2);
        });

        test('should handle invalid response format', async () => {
            mockFetch.mockResolvedValueOnce(new MockResponse(JSON.stringify({
                invalid: 'response'
            }), { 
                status: 200,
                headers: { 'content-type': 'application/json' }
            }));

            const urls = ['https://example.com'];
            const results = await ZyteService.scrapeBatch(urls);

            expect(results.size).toBe(0);
            expect(mockFetch).toHaveBeenCalledTimes(1);
        });

        test('should handle HTTP errors', async () => {
            mockFetch.mockResolvedValueOnce(new MockResponse('Rate limit exceeded', {
                status: 429,
                headers: { 'content-type': 'text/plain' }
            }));

            const urls = ['https://example.com'];
            const results = await ZyteService.scrapeBatch(urls);

            expect(results.size).toBe(0);
            expect(mockFetch).toHaveBeenCalledTimes(1);
        });
    });

    describe('Batch Processing', () => {
        test('should process multiple URLs in batches', async () => {
            // Mock successful responses for all URLs
            mockFetch.mockResolvedValue(new MockResponse(JSON.stringify(validResponse), {
                status: 200,
                headers: { 'content-type': 'application/json' }
            }));

            const urls = Array(3).fill('https://example.com');
            const results = await ZyteService.scrapeBatch(urls, {
                batchSize: 2
            });

            expect(results.size).toBe(3);
            expect(mockFetch).toHaveBeenCalledTimes(3);
        }, 10000); // Increase timeout for batch processing

        test('should handle mixed success and failures in batch', async () => {
            mockFetch
                .mockResolvedValueOnce(new MockResponse(JSON.stringify(validResponse), { 
                    status: 200,
                    headers: { 'content-type': 'application/json' }
                }))
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValueOnce(new MockResponse(JSON.stringify(validResponse), { 
                    status: 200,
                    headers: { 'content-type': 'application/json' }
                }));

            const urls = ['https://example1.com', 'https://example2.com', 'https://example3.com'];
            const results = await ZyteService.scrapeBatch(urls);

            expect(results.size).toBe(2);
            expect(mockFetch).toHaveBeenCalledTimes(3);
        });
    });
}); 