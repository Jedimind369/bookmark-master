import Anthropic from '@anthropic-ai/sdk';
import * as cheerio from 'cheerio';
import fetch from 'node-fetch';
import type { Response } from 'node-fetch';
import fs from 'fs/promises';
import path from 'path';
import Bottleneck from 'bottleneck';
import { YouTubeService, type VideoDetails } from './youtubeService';
import { EventEmitter } from 'events';

if (!process.env.ANTHROPIC_API_KEY) {
  throw new Error("ANTHROPIC_API_KEY is not set");
}

// Memory-efficient rate limiter configuration
const limiter = new Bottleneck({
  maxConcurrent: 2,
  minTime: 1000,
  reservoir: 10,
  reservoirRefreshAmount: 10,
  reservoirRefreshInterval: 60 * 1000,
  trackDoneStatus: false,
  Promise: Promise
});

// Cache and debug management
const MAX_CACHE_SIZE = 100;
const MAX_DEBUG_FILES = 50;
const MAX_LISTENERS = 10;
const promptCache = new Map<string, string>();
const analysisAttemptsMap = new Map<string, number>();
const debugFiles = new Set<string>();

// Create a memory-efficient event emitter
const progressEmitter = new EventEmitter();
progressEmitter.setMaxListeners(MAX_LISTENERS);

// the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// Create debug directory if it doesn't exist
try {
  fs.mkdir(path.join(process.cwd(), 'debug')).catch(() => {});
} catch (error) {
  console.warn('Could not create debug directory:', error);
}

export interface AIAnalysis {
  title: string;
  description: string;
  tags: string[];
  contentQuality: {
    relevance: number;
    informativeness: number;
    credibility: number;
    overallScore: number;
  };
  mainTopics: string[];
  recommendations?: {
    improvedTitle?: string;
    improvedDescription?: string;
    suggestedTags?: string[];
  };
  metadata?: {
    author?: string;
    publishDate?: string;
    lastModified?: string;
    mainImage?: string;
    wordCount?: number;
    analysisAttempts?: number;
    error?: string;
  };
}

interface PageContent {
  url: string;
  title: string;
  description: string;
  content: string;
  type: 'webpage' | 'video' | 'article' | 'product';
  metadata?: {
    author?: string;
    publishDate?: string;
    lastModified?: string;
    mainImage?: string;
    wordCount?: number;
  };
}

export interface BatchProgress {
  total: number;
  completed: number;
  failed: number;
  inProgress: number;
  errors: Array<{ url: string; error: string }>;
  startTime: Date;
  estimatedTimeRemaining?: number;
}

export interface BatchOptions {
  batchSize?: number;
  maxConcurrent?: number;
  onProgress?: (progress: BatchProgress) => void;
}

export class AIService {
  // Enhanced service with batch processing and rate limiting
  private static readonly MAX_RETRIES = 2;
  private static readonly INITIAL_RETRY_DELAY = 2000;
  private static readonly TIMEOUT = 20000;
  private static readonly DEFAULT_BATCH_SIZE = 20;
  private static readonly DEFAULT_MAX_CONCURRENT = 2;
  private static readonly MAX_CONTENT_LENGTH = 3000;
  
  private static limiter = limiter;
  private static progressEmitter = progressEmitter;

  private static async delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private static async saveDebugInfo(url: string, data: any, type: string): Promise<void> {
    try {
      const debugDir = path.join(process.cwd(), 'debug');
      
      // Limit number of debug files
      if (debugFiles.size >= MAX_DEBUG_FILES) {
        const oldestFile = Array.from(debugFiles)[0];
        await fs.unlink(path.join(debugDir, oldestFile)).catch(() => {});
        debugFiles.delete(oldestFile);
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `${type}_${encodeURIComponent(url)}_${timestamp}.json`;
      
      // Only save essential data
      const essentialData = {
        url,
        timestamp,
        type,
        error: data.error,
        summary: typeof data === 'string' ? data.slice(0, 500) : JSON.stringify(data).slice(0, 500)
      };

      await fs.writeFile(
        path.join(debugDir, filename),
        JSON.stringify(essentialData, null, 2)
      );
      debugFiles.add(filename);
    } catch (error) {
      console.warn(`Failed to save debug info for ${url}:`, error);
    }
  }

  private static async getVideoAnalysisPrompt(videoContent: VideoDetails): Promise<string> {
    return `Analyze this video content and provide a detailed analysis. Return ONLY a valid JSON object with no additional text, notes, or comments:

Title: ${videoContent.title}
Author: ${videoContent.author}
Published: ${videoContent.publishDate}
Description: ${videoContent.description}
Transcript: ${videoContent.transcript}

The response must be a valid JSON object with this exact structure:
{
  "title": "write a complete, descriptive title that accurately represents the video content",
  "description": "Write a comprehensive description (at least 5-8 detailed sentences) that covers: 
    1. The main purpose and target audience of the video
    2. Key points, demonstrations, or arguments presented
    3. Important examples or case studies discussed
    4. Practical applications or takeaways
    5. Unique insights or methodologies shared
    Include specific details from the video to support each point.",
  "tags": ["at least 5 specific, relevant tags that reflect the video topic, industry, and key concepts"],
  "contentQuality": {
    "relevance": 0.8,
    "informativeness": 0.8,
    "credibility": 0.8,
    "overallScore": 0.8
  },
  "mainTopics": ["3-4 main topics covered in detail"],
  "recommendations": {
    "improvedTitle": "enhanced title with clear value proposition",
    "improvedDescription": "alternative description with additional context",
    "suggestedTags": ["additional relevant tags"]
  }
}`;
  }

  private static async getWebAnalysisPrompt(pageContent: PageContent): Promise<string> {
    return `Analyze this ${pageContent.type} content and provide a detailed analysis. Return ONLY a valid JSON object with no additional text, notes, or comments:

URL: ${pageContent.url}
Title: ${pageContent.title}
Type: ${pageContent.type}
Description: ${pageContent.description}
Content: ${pageContent.content.slice(0, this.MAX_CONTENT_LENGTH)}

The response must be a valid JSON object with this exact structure:
{
  "title": "write a complete, descriptive title that accurately represents the content",
  "description": "Write a comprehensive description (at least 5-8 detailed sentences) that covers: 
    1. The main purpose and target audience
    2. Key features, concepts, or arguments presented
    3. Notable technical aspects or implementations
    4. Important benefits or value propositions
    5. Any unique aspects or innovations
    Include specific details from the content to support each point.",
  "tags": ["at least 5 specific, relevant tags"],
  "contentQuality": {
    "relevance": 0.8,
    "informativeness": 0.8,
    "credibility": 0.8,
    "overallScore": 0.8
  },
  "mainTopics": ["3-4 main topics covered"],
  "recommendations": {
    "improvedTitle": "enhanced title with clear value proposition",
    "improvedDescription": "alternative description with additional context",
    "suggestedTags": ["additional relevant tags"]
  }
}`;
  }

  private static async callAnthropicWithRateLimit(prompt: string): Promise<any> {
    return this.limiter.schedule(async () => {
      const response = await anthropic.messages.create({
        model: "claude-3-sonnet-20240229",
        max_tokens: 4000,
        messages: [{ role: "user", content: prompt }]
      });
      return response;
    });
  }

  private static async processAIResponse(response: any, url: string): Promise<AIAnalysis> {
    const content = response.content[0];
    if (!content || typeof content !== 'object' || !('text' in content)) {
      throw new Error('Invalid AI response structure');
    }

    let responseText = content.text.trim();
    
    // Memory optimization: Use substring instead of slice for large strings
    if (responseText.length > this.MAX_CONTENT_LENGTH) {
      responseText = responseText.substring(0, this.MAX_CONTENT_LENGTH);
    }

    const jsonMatch = responseText.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error('No valid JSON found in response');
    }

    responseText = jsonMatch[0];
    
    // Minimize debug info size
    const debugInfo = {
      timestamp: new Date().toISOString(),
      status: 'success',
      length: responseText.length
    };
    await this.saveDebugInfo(url, debugInfo, 'analysis');

    try {
      const analysis = JSON.parse(responseText);

      if (!analysis.title || !analysis.description || !Array.isArray(analysis.tags)) {
        throw new Error('Invalid analysis structure');
      }

      // Memory optimization: Use Set for deduplication
      const uniqueTags = new Set([
        ...(analysis.tags || []),
        ...(analysis.recommendations?.suggestedTags || [])
      ]);
      const combinedTags = Array.from(uniqueTags).slice(0, 10);

      if (combinedTags.length < 5) {
        throw new Error('Not enough tags generated');
      }

      return {
        title: analysis.title.substring(0, 200),
        description: analysis.description.substring(0, 1000),
        tags: combinedTags.map(tag => tag.toLowerCase()),
        contentQuality: {
          relevance: Math.max(0, Math.min(1, analysis.contentQuality?.relevance || 0.8)),
          informativeness: Math.max(0, Math.min(1, analysis.contentQuality?.informativeness || 0.8)),
          credibility: Math.max(0, Math.min(1, analysis.contentQuality?.credibility || 0.8)),
          overallScore: Math.max(0, Math.min(1, analysis.contentQuality?.overallScore || 0.8))
        },
        mainTopics: (analysis.mainTopics || []).slice(0, 4),
        recommendations: {
          improvedTitle: analysis.recommendations?.improvedTitle?.substring(0, 200),
          improvedDescription: analysis.recommendations?.improvedDescription?.substring(0, 1000),
          suggestedTags: analysis.recommendations?.suggestedTags?.slice(0, 5)
        },
        metadata: {
          analysisAttempts: 1
        }
      };
    } catch (error) {
      // Clean up on error
      this.manageCache();
      throw error;
    }
  }

  private static getAnalysisAttempts(url: string): number {
    return analysisAttemptsMap.get(url) || 0;
  }

  private static setAnalysisAttempts(url: string, attempts: number): void {
    analysisAttemptsMap.set(url, attempts);
  }

  private static async analyzeContentWithRetry(url: string, content: PageContent): Promise<AIAnalysis> {
    let lastError: Error | null = null;
    const attempts = this.getAnalysisAttempts(url);

    for (let i = 0; i < this.MAX_RETRIES; i++) {
      try {
        const prompt = content.type === 'video' 
          ? await this.getVideoAnalysisPrompt(content as unknown as VideoDetails)
          : await this.getWebAnalysisPrompt(content);
        const response = await this.callAnthropicWithRateLimit(prompt);
        return await this.processAIResponse(response, url);
      } catch (error) {
        lastError = error as Error;
        const delay = this.INITIAL_RETRY_DELAY * Math.pow(2, i);
        await this.delay(delay);
      }
    }

    this.setAnalysisAttempts(url, attempts + 1);
    throw lastError || new Error('Failed to analyze content after multiple retries');
  }

  private static async fetchPageContent(url: string): Promise<PageContent> {
    try {
      console.log(`[Analysis] Fetching content for: ${url}`);
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), this.TIMEOUT);

      try {
        if (url.includes('youtube.com') || url.includes('youtu.be')) {
          console.log('[Analysis] Detected YouTube URL');
          const videoContent = await YouTubeService.getVideoContent(url);
          if (!videoContent) {
            throw new Error('Failed to fetch YouTube content');
          }

          return {
            url,
            title: videoContent.title,
            description: videoContent.description,
            content: JSON.stringify(videoContent), // Changed to stringify VideoDetails
            type: 'video',
            metadata: {
              author: videoContent.author,
              publishDate: videoContent.publishDate
            }
          };
        }

        const response = await fetch(url, {
          headers: {
            'Accept': 'text/html,application/xhtml+xml',
            'User-Agent': 'Mozilla/5.0 (compatible; BookmarkAnalyzer/1.0)'
          },
          signal: controller.signal
        });

        if (!response.ok || !response.body) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Stream and process content in chunks
        const chunks: Buffer[] = [];
        let totalSize = 0;
        const MAX_SIZE = 1024 * 1024; // 1MB limit

        for await (const chunk of response.body) {
          totalSize += chunk.length;
          if (totalSize > MAX_SIZE) {
            console.warn(`[Analysis] Content too large for ${url}, truncating`);
            break;
          }
          chunks.push(Buffer.from(chunk));
        }

        const html = Buffer.concat(chunks).toString('utf-8');
        const $ = cheerio.load(html);

        // Clean up unnecessary elements to reduce memory
        $('script, style, iframe, noscript').remove();

        // Extract content with memory efficiency
        const title = $('meta[property="og:title"]').attr('content') || 
                     $('title').text() || 
                     url.split('/').pop() || 
                     'Untitled';

        const description = $('meta[property="og:description"]').attr('content') || 
                          $('meta[name="description"]').attr('content') || 
                          '';

        // Extract main content more efficiently
        const mainContent = $('article, main, .content')
          .map((_, el) => $(el).text())
          .get()
          .join(' ')
          .replace(/\s+/g, ' ')
          .trim()
          .slice(0, this.MAX_CONTENT_LENGTH);

        const type: PageContent['type'] = $('article').length ? 'article' : 'webpage';

        return {
          url,
          title: title.slice(0, 200),  // Limit title length
          description: description.slice(0, 500),  // Limit description length
          content: mainContent,
          type,
          metadata: {
            author: $('meta[name="author"]').attr('content')?.slice(0, 100),
            publishDate: $('meta[property="article:published_time"]').attr('content'),
            mainImage: $('meta[property="og:image"]').attr('content')
          }
        };
      } finally {
        clearTimeout(timeout);
      }
    } catch (error) {
      console.error('[Analysis] Fetch error:', error);
      throw error;
    }
  }

  static async analyzeUrl(url: string): Promise<AIAnalysis> {
    try {
      const content = await this.fetchPageContent(url);
      return this.analyzeContentWithRetry(url, content);
    } catch (error) {
      console.error(`[Analysis] Failed to analyze URL ${url}:`, error);
      throw error;
    }
  }

  static async analyzeBatch(
    urls: string[],
    options: BatchOptions = {}
  ): Promise<Map<string, AIAnalysis>> {
    const {
      batchSize = this.DEFAULT_BATCH_SIZE,
      maxConcurrent = this.DEFAULT_MAX_CONCURRENT,
      onProgress
    } = options;

    const results = new Map<string, AIAnalysis>();
    const progress: BatchProgress = {
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
          const result = await this.analyzeUrl(url);
          results.set(url, result);
          progress.completed++;
        } catch (error) {
          progress.failed++;
          progress.errors.push({
            url,
            error: error instanceof Error ? error.message : 'Unknown error'
          });
          console.error(`[Batch] Failed to analyze ${url}:`, error);
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

  private static updateEstimatedTimeRemaining(progress: BatchProgress): void {
    const elapsed = Date.now() - progress.startTime.getTime();
    const completedCount = progress.completed + progress.failed;
    if (completedCount === 0) return;

    const averageTimePerUrl = elapsed / completedCount;
    const remainingUrls = progress.total - completedCount;
    progress.estimatedTimeRemaining = averageTimePerUrl * remainingUrls;
  }

  private static updateProgress(
    progress: BatchProgress,
    onProgress?: (progress: BatchProgress) => void
  ): void {
    if (onProgress) {
      onProgress(progress);
    }
    this.progressEmitter.emit('progress', progress);
  }

  static onProgress(callback: (progress: BatchProgress) => void): () => void {
    this.progressEmitter.on('progress', callback);
    // Return cleanup function
    return () => this.progressEmitter.removeListener('progress', callback);
  }

  // Cache management
  private static manageCache(): void {
    if (promptCache.size > MAX_CACHE_SIZE) {
      const keysToDelete = Array.from(promptCache.keys()).slice(0, MAX_CACHE_SIZE / 2);
      keysToDelete.forEach(key => promptCache.delete(key));
    }
  }

  // Add cleanup method
  static cleanup(): void {
    this.progressEmitter.removeAllListeners();
    promptCache.clear();
    analysisAttemptsMap.clear();
    debugFiles.clear();
  }
}