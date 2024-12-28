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
  private static readonly TIMEOUT = 30000; // 30 seconds

  private static async delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private static async exponentialBackoff(attempt: number): Promise<void> {
    const delay = this.INITIAL_RETRY_DELAY * Math.pow(2, attempt);
    await this.delay(delay);
  }

  private static normalizeUrl(url: string): string {
    try {
      if (!url) throw new Error('URL is required');

      let normalizedUrl = url.trim();
      if (normalizedUrl.startsWith('www.')) {
        normalizedUrl = 'https://' + normalizedUrl;
      }
      if (normalizedUrl.startsWith('http://')) {
        normalizedUrl = 'https://' + normalizedUrl.slice(7);
      }
      if (!normalizedUrl.startsWith('http')) {
        normalizedUrl = 'https://' + normalizedUrl;
      }

      const parsedUrl = new URL(normalizedUrl);
      return parsedUrl.toString().replace(/\/$/, '');
    } catch (error) {
      throw new Error(`Invalid URL format: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private static async fetchWithTimeout(url: string, options: any = {}, timeout = 30000): Promise<Response> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(id);
      return response;
    } catch (error) {
      clearTimeout(id);
      throw error;
    }
  }

  private static async fetchWithRetry(url: string, retries = 0): Promise<PageContent> {
    try {
      console.log(`[Analysis] Attempting to fetch ${url} (attempt ${retries + 1})`);

      // Configure browser-like headers
      const headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      };

      // Single fetch with human-like behavior
      const response = await this.fetchWithTimeout(url, {
        headers: {
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'Accept-Encoding': 'gzip, deflate, br',
          'Connection': 'keep-alive',
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
          'sec-ch-ua': '"Chromium";v="122", "Google Chrome";v="122"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"Windows"',
          'Sec-Fetch-Dest': 'document',
          'Sec-Fetch-Mode': 'navigate',
          'Sec-Fetch-Site': 'none',
          'Sec-Fetch-User': '?1',
          'Upgrade-Insecure-Requests': '1'
        },
        credentials: 'include',
        referrer: 'https://www.google.com/',
        referrerPolicy: 'strict-origin-when-cross-origin',
        mode: 'cors'
      }, this.TIMEOUT);

      const contentType = response.headers.get('content-type');
      if (!response.ok || (contentType && !contentType.includes('text/html'))) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const html = await response.text();
      if (html.trim().startsWith('<!DOCTYPE')) {
        const $ = cheerio.load(html);
        const title = $('title').text() || url;
        return {
          url,
          title,
          description: `Failed to fetch page: ${response.status} ${response.statusText}`,
          content: $('body').text().trim(),
          type: 'webpage', // Assuming webpage type for failed fetches
          metadata: {} // Empty metadata for failed fetches
        };
      }


      if (!html || html.length < 100) {
        throw new Error('Empty or too short response');
      }

      const $ = cheerio.load(html);

      // Check for CAPTCHA
      const captchaIndicators = [
        'captcha',
        'robot check',
        'verify human',
        'security check',
        'please verify',
        'bot check'
      ];

      const pageText = $('body').text().toLowerCase();
      const captchaDetected = captchaIndicators.some(indicator =>
        pageText.includes(indicator.toLowerCase())
      );

      if (captchaDetected) {
        // For YouTube URLs, use alternative metadata extraction
        if (url.includes('youtube.com') || url.includes('youtu.be')) {
          const videoId = url.includes('youtube.com/watch?v=') 
            ? new URL(url).searchParams.get('v')
            : url.split('/').pop();
            
          return {
            url,
            title: $('meta[property="og:title"]').attr('content') || 'YouTube Video',
            description: $('meta[property="og:description"]').attr('content') || 'YouTube video content',
            content: $('meta[property="og:description"]').attr('content') || '',
            type: 'video',
            metadata: {
              author: $('meta[name="author"]').attr('content'),
              publishDate: $('meta[property="article:published_time"]').attr('content'),
              mainImage: `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`
            }
          };
        }
        
        throw new Error('CAPTCHA detected');
      }

      // Remove non-content elements
      $('script, style, nav, footer, iframe, noscript').remove();
      $('.cookie-banner, .advertisement, .popup, .modal').remove();
      $('[class*="cookie"], [class*="banner"], [class*="popup"]').remove();

      const title = $('meta[property="og:title"]').attr('content')?.trim() ||
                   $('title').text().trim() ||
                   $('h1').first().text().trim() ||
                   'Untitled Page';

      const metaDescription = $('meta[property="og:description"]').attr('content')?.trim() ||
                            $('meta[name="description"]').attr('content')?.trim() ||
                            '';

      // Get main content with better fallbacks
      let mainContent = '';
      const contentSelectors = [
        'article',
        '[role="main"]',
        'main',
        '#content',
        '.content',
        '.article',
        '.post'
      ];

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

      if (!mainContent) {
        throw new Error('No meaningful content found');
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

      throw error;
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

      const content = response.content[0];
      if (!content || typeof content.text !== 'string') {
        throw new Error("Invalid response from Claude");
      }

      console.log(`[Analysis] Raw analysis result:`, content.text);

      let analysis: AIAnalysis;
      try {
        // Clean the response text to ensure valid JSON
        const cleanText = content.text.trim();
        // Handle potential markdown code blocks
        const jsonText = cleanText.replace(/```json\n?(.*)\n?```/s, '$1').trim();
        analysis = JSON.parse(jsonText);
      } catch (error) {
        console.error("[Analysis] JSON parse error:", error);
        console.error("[Analysis] Raw text:", content.text);
        throw new Error(`Failed to parse analysis result: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }

      // Validate and normalize the analysis
      return {
        ...analysis,
        title: (analysis.title || pageContent.title).slice(0, 60),
        description: (analysis.description || pageContent.description).slice(0, 160),
        tags: (analysis.tags || []).slice(0, 5).map(tag => tag.toLowerCase()),
        contentQuality: {
          relevance: Math.max(0, Math.min(1, analysis.contentQuality?.relevance || 0)),
          informativeness: Math.max(0, Math.min(1, analysis.contentQuality?.informativeness || 0)),
          credibility: Math.max(0, Math.min(1, analysis.contentQuality?.credibility || 0)),
          overallScore: Math.max(0, Math.min(1, analysis.contentQuality?.overallScore || 0))
        },
        mainTopics: (analysis.mainTopics || []).slice(0, 3),
        metadata: pageContent.metadata,
        recommendations: analysis.recommendations || {}
      };

    } catch (error) {
      console.error('[Analysis] Error in analyzeUrl:', error);

      // Handle rate limits with retries
      if (error instanceof Error &&
          (error.message.includes('rate') || error.message.includes('timeout')) &&
          retries < this.MAX_RETRIES) {
        console.log(`[Analysis] Rate limit/timeout hit, retrying after backoff (attempt ${retries + 1})`);
        await this.exponentialBackoff(retries);
        return this.analyzeUrl(url, retries + 1);
      }

      // Create meaningful fallback analysis
      try {
        const urlParts = new URL(url);
        const domain = urlParts.hostname.replace(/^www\./, '');
        const path = urlParts.pathname.replace(/\/$/, '');

        return {
          title: `${domain}${path}`,
          description: `Unable to analyze: ${error instanceof Error ? error.message : 'Unknown error'}. Will retry automatically.`,
          tags: ['pending-analysis', 'retry-needed'],
          contentQuality: {
            relevance: 0,
            informativeness: 0,
            credibility: 0,
            overallScore: 0
          },
          mainTopics: ['analysis-pending'],
          recommendations: {
            improvedTitle: domain,
            improvedDescription: 'Content analysis temporarily unavailable. Will retry later.',
            suggestedTags: ['needs-reanalysis']
          }
        };
      } catch (urlError) {
        return {
          title: 'Invalid URL',
          description: 'The provided URL could not be processed or analyzed',
          tags: ['error', 'invalid-url'],
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