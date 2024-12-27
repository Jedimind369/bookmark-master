import Anthropic from '@anthropic-ai/sdk';
import * as cheerio from "cheerio";
import fetch from "node-fetch";
import type { Response } from "node-fetch";

if (!process.env.ANTHROPIC_API_KEY) {
  throw new Error("ANTHROPIC_API_KEY is not set");
}

// Using Claude 3 Haiku for cost-effective but powerful analysis
const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

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
  };
}

interface PageContent {
  url: string;
  title: string;
  description: string;
  content: string;
  type?: 'webpage' | 'video' | 'article' | 'product';
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
  private static readonly INITIAL_RETRY_DELAY = 1000; // 1 second

  private static async delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private static async exponentialBackoff(attempt: number): Promise<void> {
    const delay = this.INITIAL_RETRY_DELAY * Math.pow(2, attempt);
    await this.delay(delay);
  }

  private static normalizeUrl(url: string): string {
    try {
      if (url.startsWith('www.')) {
        url = 'https://' + url;
      }
      if (url.startsWith('http://')) {
        url = 'https://' + url.slice(7);
      }
      if (!url.startsWith('http')) {
        url = 'https://' + url;
      }
      const parsedUrl = new URL(url);
      return parsedUrl.toString().replace(/\/$/, '');
    } catch (error) {
      throw new Error('Invalid URL format');
    }
  }

  private static async fetchWithRetry(url: string, retries = 0): Promise<PageContent> {
    try {
      console.log(`[Analysis] Attempting to fetch ${url} (attempt ${retries + 1})`);

      const proxyUrl = `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(url)}`;
      const response = await fetch(proxyUrl, {
        headers: {
          'Accept': 'text/html',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const html = await response.text();
      const $ = cheerio.load(html);

      // Remove non-content elements
      $('script, style, nav, footer, iframe, noscript').remove();
      $('.cookie-banner, .advertisement').remove();
      $('[class*="cookie"], [class*="banner"]').remove();

      const title = $('meta[property="og:title"]').attr('content')?.trim() ||
                   $('title').text().trim() ||
                   $('h1').first().text().trim() ||
                   'Untitled Page';

      const metaDescription = $('meta[property="og:description"]').attr('content')?.trim() ||
                            $('meta[name="description"]').attr('content')?.trim() ||
                            '';

      // Get main content
      let mainContent = '';
      const contentSelectors = ['article', '[role="main"]', 'main', '#content', '.content'];

      for (const selector of contentSelectors) {
        const element = $(selector).first();
        if (element.length) {
          mainContent = element.text().trim();
          break;
        }
      }

      if (!mainContent) {
        mainContent = $('body').clone()
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
        wordCount: mainContent.split(/\s+/).length
      };

      // Determine content type
      let type: 'webpage' | 'video' | 'article' | 'product' = 'webpage';
      if ($('[itemtype*="Product"]').length || $('.price').length) {
        type = 'product';
      } else if ($('article').length || $('[itemtype*="Article"]').length) {
        type = 'article';
      }

      return {
        url,
        title,
        description: metaDescription,
        content: [title, metaDescription, mainContent]
          .filter(Boolean)
          .join('\n\n')
          .replace(/\s+/g, ' ')
          .trim()
          .slice(0, 1500), // Reduced content length for efficiency
        type,
        metadata
      };

    } catch (error) {
      console.error(`[Analysis] Error fetching ${url}:`, error);

      if (retries < this.MAX_RETRIES) {
        console.warn(`[Analysis] Retrying ${url} (attempt ${retries + 1})`);
        await this.exponentialBackoff(retries);
        return this.fetchWithRetry(url, retries + 1);
      }

      throw new Error(`Failed to fetch page: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  static async analyzeUrl(url: string, retries = 0): Promise<AIAnalysis> {
    try {
      const normalizedUrl = this.normalizeUrl(url);
      console.log(`[Analysis] Starting analysis of: ${normalizedUrl}`);

      const pageContent = await this.fetchWithRetry(normalizedUrl);
      console.log(`[Analysis] Successfully fetched page content`);

      const response = await anthropic.messages.create({
        model: "claude-3-haiku-20240307",
        max_tokens: 1024,
        temperature: 0.3,
        system: `You are a content analyst. Analyze web content and return a JSON response with:
{
  "title": "<60 char title",
  "description": "<160 char summary",
  "tags": ["3-5 tags"],
  "contentQuality": {
    "relevance": 0-1,
    "informativeness": 0-1,
    "credibility": 0-1,
    "overallScore": 0-1
  },
  "mainTopics": ["2-3 topics"],
  "recommendations": {
    "improvedTitle": "optional",
    "improvedDescription": "optional",
    "suggestedTags": ["optional"]
  }
}`,
        messages: [{
          role: "user",
          content: `Analyze:
URL: ${pageContent.url}
Title: ${pageContent.title}
Type: ${pageContent.type}
Content: ${pageContent.content}`
        }]
      });

      const result = response.content[0].text;
      if (!result) {
        throw new Error("No response from Claude");
      }

      console.log(`[Analysis] Raw analysis result:`, result);
      const analysis = JSON.parse(result);

      return {
        ...analysis,
        title: analysis.title.slice(0, 60),
        description: analysis.description.slice(0, 160),
        tags: analysis.tags.slice(0, 5).map((tag: string) => tag.toLowerCase()),
        contentQuality: {
          relevance: Math.max(0, Math.min(1, analysis.contentQuality.relevance)),
          informativeness: Math.max(0, Math.min(1, analysis.contentQuality.informativeness)),
          credibility: Math.max(0, Math.min(1, analysis.contentQuality.credibility)),
          overallScore: Math.max(0, Math.min(1, analysis.contentQuality.overallScore))
        },
        mainTopics: analysis.mainTopics.slice(0, 3),
        metadata: pageContent.metadata
      };
    } catch (error) {
      console.error('[Analysis] Error in analyzeUrl:', error);

      // Handle rate limits with retries
      if (error instanceof Error && 
          error.message.includes('rate') && 
          retries < this.MAX_RETRIES) {
        console.log(`[Analysis] Rate limit hit, retrying after backoff (attempt ${retries + 1})`);
        await this.exponentialBackoff(retries);
        return this.analyzeUrl(url, retries + 1);
      }

      // Create meaningful fallback analysis
      try {
        const urlParts = new URL(url);
        return {
          title: urlParts.hostname,
          description: `Content temporarily unavailable - ${error instanceof Error ? error.message : 'Analysis error'}`,
          tags: ['pending-analysis'],
          contentQuality: {
            relevance: 0,
            informativeness: 0,
            credibility: 0,
            overallScore: 0
          },
          mainTopics: ['analysis-pending'],
          recommendations: {
            improvedTitle: 'Analysis will be retried later',
            improvedDescription: 'Content analysis temporarily unavailable. Will retry automatically.',
            suggestedTags: ['needs-reanalysis']
          }
        };
      } catch {
        return {
          title: 'Invalid URL',
          description: 'The provided URL could not be processed',
          tags: ['error', 'invalid'],
          contentQuality: {
            relevance: 0,
            informativeness: 0,
            credibility: 0,
            overallScore: 0
          },
          mainTopics: ['unknown'],
          recommendations: {
            improvedTitle: 'Invalid URL Entry',
            improvedDescription: 'Please provide a valid URL for analysis',
            suggestedTags: ['invalid-url']
          }
        };
      }
    }
  }
}