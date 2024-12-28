import Anthropic from '@anthropic-ai/sdk';
import * as cheerio from 'cheerio';
import fetch from 'node-fetch';
import type { Response } from 'node-fetch';
import fs from 'fs/promises';
import path from 'path';
import { YouTubeService } from './youtubeService';
import type { BookmarkAnalysis, BookmarkMetadata } from '@shared/types/bookmark';
import { AnalysisStatus } from '@shared/types/bookmark';

// Verify API key is set
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
if (!ANTHROPIC_API_KEY) {
  throw new Error("ANTHROPIC_API_KEY is not set");
}

const anthropic = new Anthropic({
  apiKey: ANTHROPIC_API_KEY
});

// Create debug directory if it doesn't exist
const debugDir = path.join(process.cwd(), 'debug');
fs.mkdir(debugDir).catch(() => {
  // Ignore error if directory already exists
});

interface PageContent {
  url: string;
  title: string;
  description: string;
  content: string;
  type: 'webpage' | 'video' | 'article' | 'product';
  metadata?: BookmarkMetadata;
}

export class AIService {
  private static readonly MAX_RETRIES = 3;
  private static readonly INITIAL_RETRY_DELAY = 1000;
  private static readonly TIMEOUT = 30000;
  private static analysisAttempts: Map<string, number> = new Map();

  private static async delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private static async exponentialBackoff(attempt: number): Promise<void> {
    const delay = this.INITIAL_RETRY_DELAY * Math.pow(2, attempt);
    await this.delay(delay);
  }

  private static async saveDebugInfo(url: string, data: any, type: string): Promise<void> {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `${type}_${encodeURIComponent(url)}_${timestamp}.json`;
      await fs.writeFile(
        path.join(debugDir, filename),
        JSON.stringify(data, null, 2)
      );
    } catch (error) {
      console.warn(`Failed to save debug info for ${url}:`, error);
    }
  }

  private static isValidHtml(text: string): boolean {
    const htmlPatterns = [
      /^\s*<!DOCTYPE\s+html/i,
      /^\s*<html/i,
      /<head>/i,
      /<body>/i,
      /<\/html>/i
    ];
    return htmlPatterns.some(pattern => pattern.test(text));
  }

  private static async fetchWithTimeout(
    url: string,
    options: any = {},
    timeout: number = 30000
  ): Promise<Response> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      return response;
    } finally {
      clearTimeout(id);
    }
  }

  private static normalizeUrl(url: string): string {
    try {
      let normalizedUrl = url.trim();
      if (!normalizedUrl) {
        throw new Error('URL is required');
      }

      // Add https:// if no protocol specified
      if (!normalizedUrl.match(/^https?:\/\//i)) {
        normalizedUrl = 'https://' + normalizedUrl;
      }

      // Convert http to https
      normalizedUrl = normalizedUrl.replace(/^http:/i, 'https:');

      // Validate URL format
      const parsedUrl = new URL(normalizedUrl);

      // Remove trailing slash
      return parsedUrl.toString().replace(/\/$/, '');
    } catch (error) {
      throw new Error(`Invalid URL format: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private static async analyzeVideoContent(pageContent: PageContent): Promise<BookmarkAnalysis> {
    try {
      console.log(`[Video Analysis] Starting analysis for: ${pageContent.url}`);

      // Get basic metadata from YouTube
      const metadata = await YouTubeService.getMetadata(pageContent.url);

      if (!metadata) {
        throw new Error('Could not fetch video metadata');
      }

      return {
        title: metadata.title,
        description: metadata.description,
        tags: ['video', 'youtube'],
        contentQuality: {
          relevance: 0.8,
          informativeness: 0.8,
          credibility: 0.8,
          overallScore: 0.8
        },
        mainTopics: ['video content'],
        recommendations: {},
        metadata: {
          thumbnailUrl: metadata.thumbnailUrl,
          analysisAttempts: 1,
          status: AnalysisStatus.Success
        }
      };
    } catch (error) {
      console.error('[Video Analysis] Error:', error);
      return this.createFallbackAnalysis(pageContent, error instanceof Error ? error.message : 'Unknown error');
    }
  }

  private static createFallbackAnalysis(pageContent: PageContent, errorReason: string): BookmarkAnalysis {
    console.log('[Analysis] Creating fallback analysis due to:', errorReason);

    return {
      title: pageContent.title || pageContent.url,
      description: pageContent.description || 'Content analysis temporarily unavailable',
      tags: ['analysis-pending'],
      contentQuality: {
        relevance: 0.5,
        informativeness: 0.5,
        credibility: 0.5,
        overallScore: 0.5
      },
      mainTopics: ['content-pending'],
      metadata: {
        analysisAttempts: 1,
        error: errorReason,
        status: AnalysisStatus.Error
      },
      recommendations: {}
    };
  }

  private static normalizeScore(score: any): number {
    const num = typeof score === 'number' ? score : parseFloat(score);
    if (isNaN(num)) return 0.5;
    return Math.max(0, Math.min(1, num));
  }

  private static extractKeywordsFromContent(content: string): string[] {
    const words = content.toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 3);

    const wordFreq: Record<string, number> = {};
    words.forEach(word => {
      wordFreq[word] = (wordFreq[word] || 0) + 1;
    });

    return Object.entries(wordFreq)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([word]) => word);
  }

  private static extractKeywordsFromTranscript(transcript: string): string[] {
    // Extract important keywords from transcript
    const words = transcript.toLowerCase().split(/\s+/);
    const wordFreq: Record<string, number> = {};

    // Count word frequencies
    words.forEach(word => {
      if (word.length > 3) { // Skip short words
        wordFreq[word] = (wordFreq[word] || 0) + 1;
      }
    });

    // Sort by frequency and get top keywords
    return Object.entries(wordFreq)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([word]) => word);
  }


  private static async fetchPageContent(url: string, retries: number = 0): Promise<PageContent> {
    try {
      console.log(`[Analysis] Fetching ${url} (attempt ${retries + 1}/${this.MAX_RETRIES})`);

      const response = await this.fetchWithTimeout(url, {
        headers: {
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'User-Agent': 'Mozilla/5.0 (compatible; BookmarkAnalyzer/1.0; +http://localhost)',
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      }, this.TIMEOUT);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('text/html') && !contentType.includes('application/xhtml+xml')) {
        throw new Error(`Unsupported content type: ${contentType}`);
      }

      const html = await response.text();

      // Save raw HTML for debugging
      await this.saveDebugInfo(url, { html: html.slice(0, 5000) }, 'raw_html');

      if (!html || html.length < 100) {
        throw new Error('Empty or too short response');
      }

      if (!this.isValidHtml(html)) {
        throw new Error('Invalid HTML structure');
      }

      const $ = cheerio.load(html);

      // Determine content type first
      let type: PageContent['type'] = 'webpage';
      if (url.includes('youtube.com') || url.includes('youtu.be')) {
        type = 'video';
      } else if ($('[itemtype*="Product"]').length || $('.price').length) {
        type = 'product';
      } else if ($('article').length || $('[itemtype*="Article"]').length) {
        type = 'article';
      }

      // Extract content based on type
      let content = '';
      if (type === 'video') {
        content = $('meta[name="description"]').attr('content') ||
          $('.watch-main-col .content').text() ||
          $('meta[property="og:description"]').attr('content') || '';
      } else {
        const contentSelectors = [
          'article', 'main', '[role="main"]', '#content', '.content',
          '.article', '.post', '.entry-content'
        ];

        for (const selector of contentSelectors) {
          const element = $(selector).first();
          if (element.length) {
            content = element.text().trim();
            break;
          }
        }

        // Fallback to body content if no main content found
        if (!content) {
          content = $('body').clone()
            .children('nav,header,footer,aside,script,style')
            .remove()
            .end()
            .text()
            .trim();
        }
      }

      // Basic metadata extraction
      const title = $('meta[property="og:title"]').attr('content')?.trim() ||
        $('title').text().trim() ||
        $('h1').first().text().trim() ||
        url;

      const description = $('meta[property="og:description"]').attr('content')?.trim() ||
        $('meta[name="description"]').attr('content')?.trim() ||
        '';

      // Extract metadata
      const metadata = {
        author: $('meta[name="author"]').attr('content') ||
          $('[rel="author"]').first().text(),
        publishDate: $('meta[property="article:published_time"]').attr('content') ||
          $('time[pubdate]').attr('datetime'),
        lastModified: $('meta[property="article:modified_time"]').attr('content'),
        mainImage: $('meta[property="og:image"]').attr('content'),
        wordCount: content.split(/\s+/).length
      };

      return {
        url,
        title,
        description,
        content: content.replace(/\s+/g, ' ').trim(),
        type,
        metadata
      };
    } catch (error) {
      console.error(`[Analysis] Error fetching ${url}:`, error);

      if (retries < this.MAX_RETRIES) {
        await this.exponentialBackoff(retries);
        return this.fetchPageContent(url, retries + 1);
      }

      throw error;
    }
  }

  static async analyzeUrl(url: string): Promise<BookmarkAnalysis> {
    const normalizedUrl = this.normalizeUrl(url);
    const attempts = (this.analysisAttempts.get(normalizedUrl) || 0) + 1;
    this.analysisAttempts.set(normalizedUrl, attempts);

    try {
      console.log(`[Analysis] Starting analysis of ${normalizedUrl} (attempt ${attempts})`);

      const pageContent = await this.fetchPageContent(normalizedUrl);
      console.log(`[Analysis] Successfully fetched content for ${normalizedUrl}`);

      // Save extracted content for debugging
      await this.saveDebugInfo(normalizedUrl, pageContent, 'extracted_content');

      // Use different analysis strategies based on content type
      const analysis = pageContent.type === 'video'
        ? await this.analyzeVideoContent(pageContent)
        : await this.analyzeWebContent(pageContent);

      console.log(`[Analysis] Successfully analyzed ${normalizedUrl}`);
      return {
        ...analysis,
        metadata: {
          ...analysis.metadata,
          analysisAttempts: attempts
        }
      };

    } catch (error) {
      console.error(`[Analysis] Error analyzing ${normalizedUrl}:`, error);

      // Create a meaningful fallback analysis for errors
      return {
        title: url,
        description: `Analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}. Will retry automatically.`,
        tags: ['analysis-failed', 'retry-needed'],
        contentQuality: {
          relevance: 0,
          informativeness: 0,
          credibility: 0,
          overallScore: 0
        },
        mainTopics: ['analysis-pending'],
        recommendations: {
          improvedTitle: url,
          improvedDescription: 'Content analysis temporarily unavailable',
          suggestedTags: ['needs-reanalysis']
        },
        metadata: {
          analysisAttempts: attempts,
          status: AnalysisStatus.Error
        }
      };
    }
  }
}