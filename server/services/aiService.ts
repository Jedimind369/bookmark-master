import Anthropic from '@anthropic-ai/sdk';
import * as cheerio from 'cheerio';
import fetch from 'node-fetch';
import type { Response } from 'node-fetch';
import fs from 'fs/promises';
import path from 'path';

if (!process.env.ANTHROPIC_API_KEY) {
  throw new Error("ANTHROPIC_API_KEY is not set");
}

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
      const debugDir = path.join(process.cwd(), 'debug');
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

  private static async analyzeVideoContent(pageContent: PageContent): Promise<AIAnalysis> {
    try {
      const message = await anthropic.messages.create({
        model: "claude-3-5-sonnet-20241022",
        max_tokens: 1024,
        temperature: 0.3,
        messages: [{
          role: "user",
          content: [
            {
              type: "text",
              text: `Analyze this video content and metadata:
Title: ${pageContent.title}
Description: ${pageContent.description}
Author: ${pageContent.metadata?.author || 'Unknown'}
Type: ${pageContent.type}
Additional Content: ${pageContent.content}

Please provide a concise analysis in JSON format with:
1. A clear, engaging title (max 60 chars)
2. A comprehensive description (max 160 chars)
3. 3-5 relevant tags
4. Content quality metrics
5. Main topics covered`
            }
          ]
        }]
      });

      // Get the first response with content
      const content = message.content[0]?.text;
      if (!content) {
        throw new Error('No content in AI response');
      }

      // Save response for debugging
      await this.saveDebugInfo(pageContent.url, { aiResponse: content }, 'video_analysis');

      try {
        const analysis = JSON.parse(content);
        return {
          title: (analysis.title || pageContent.title).slice(0, 60),
          description: (analysis.description || pageContent.description).slice(0, 160),
          tags: (analysis.tags || ['video']).slice(0, 5).map((tag: string) => tag.toLowerCase()),
          contentQuality: {
            relevance: Math.max(0, Math.min(1, analysis.contentQuality?.relevance || 0.7)),
            informativeness: Math.max(0, Math.min(1, analysis.contentQuality?.informativeness || 0.7)),
            credibility: Math.max(0, Math.min(1, analysis.contentQuality?.credibility || 0.8)),
            overallScore: Math.max(0, Math.min(1, analysis.contentQuality?.overallScore || 0.75))
          },
          mainTopics: (analysis.mainTopics || ['video content']).slice(0, 3),
          metadata: {
            ...pageContent.metadata,
            analysisAttempts: 1
          }
        };
      } catch (parseError) {
        console.error('[Video Analysis] Failed to parse AI response:', parseError);
        throw new Error('Invalid video analysis format');
      }
    } catch (error) {
      console.error('[Video Analysis] Error:', error);
      throw error;
    }
  }

  private static async analyzeWebContent(pageContent: PageContent): Promise<AIAnalysis> {
    const message = await anthropic.messages.create({
      model: "claude-3-5-sonnet-20241022",
      max_tokens: 1024,
      temperature: 0.3,
      messages: [{
        role: "user",
        content: [
          {
            type: "text",
            text: `Analyze this webpage content and return a JSON response:
URL: ${pageContent.url}
Title: ${pageContent.title}
Type: ${pageContent.type}
Description: ${pageContent.description}
Content: ${pageContent.content.slice(0, 2000)}

Required JSON format:
{
  "title": "<60 char title>",
  "description": "<160 char summary>",
  "tags": ["3-5 relevant tags"],
  "contentQuality": {
    "relevance": <0-1 score>,
    "informativeness": <0-1 score>,
    "credibility": <0-1 score>,
    "overallScore": <0-1 average>
  },
  "mainTopics": ["2-3 main topics"],
  "recommendations": {
    "improvedTitle": "optional better title",
    "improvedDescription": "optional better description",
    "suggestedTags": ["optional better tags"]
  }
}`
          }
        ]
      }]
    });

    // Get the first response with content
    const content = message.content[0]?.text;
    if (!content) {
      throw new Error('No content in AI response');
    }

    // Save response for debugging
    await this.saveDebugInfo(pageContent.url, { aiResponse: content }, 'web_analysis');

    try {
      const analysis = JSON.parse(content);
      return {
        title: (analysis.title || pageContent.title).slice(0, 60),
        description: (analysis.description || pageContent.description).slice(0, 160),
        tags: (analysis.tags || []).slice(0, 5).map((tag: string) => tag.toLowerCase()),
        contentQuality: {
          relevance: Math.max(0, Math.min(1, analysis.contentQuality?.relevance || 0)),
          informativeness: Math.max(0, Math.min(1, analysis.contentQuality?.informativeness || 0)),
          credibility: Math.max(0, Math.min(1, analysis.contentQuality?.credibility || 0)),
          overallScore: Math.max(0, Math.min(1, analysis.contentQuality?.overallScore || 0))
        },
        mainTopics: (analysis.mainTopics || []).slice(0, 3),
        recommendations: analysis.recommendations || {},
        metadata: {
          ...pageContent.metadata,
          analysisAttempts: 1
        }
      };
    } catch (parseError) {
      console.error('[Web Analysis] Failed to parse AI response:', parseError);
      throw new Error('Invalid analysis format');
    }
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

      // Save response headers for debugging
      await this.saveDebugInfo(url, {
        status: response.status,
        headers: Object.fromEntries(response.headers.entries())
      }, 'response_headers');

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('text/html') && !contentType.includes('application/xhtml+xml')) {
        throw new Error(`Unsupported content type: ${contentType}`);
      }

      const html = await response.text();

      // Save raw HTML for debugging
      await this.saveDebugInfo(url, { html }, 'raw_html');

      if (!html || html.length < 100) {
        throw new Error('Empty or too short response');
      }

      if (!this.isValidHtml(html)) {
        throw new Error('Invalid HTML structure');
      }

      const $ = cheerio.load(html);

      // Basic content extraction
      const title = $('meta[property="og:title"]').attr('content')?.trim() ||
                   $('title').text().trim() ||
                   $('h1').first().text().trim() ||
                   url;

      const description = $('meta[property="og:description"]').attr('content')?.trim() ||
                         $('meta[name="description"]').attr('content')?.trim() ||
                         '';

      // Get main content
      let content = '';
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
          .children('nav,header,footer,aside')
          .remove()
          .end()
          .text()
          .trim();
      }

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

      // Determine content type
      let type: PageContent['type'] = 'webpage';
      if (url.includes('youtube.com') || url.includes('vimeo.com')) {
        type = 'video';
      } else if ($('[itemtype*="Product"]').length || $('.price').length) {
        type = 'product';
      } else if ($('article').length || $('[itemtype*="Article"]').length) {
        type = 'article';
      }

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

  static async analyzeUrl(url: string): Promise<AIAnalysis> {
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
          analysisAttempts: attempts
        }
      };
    }
  }
}