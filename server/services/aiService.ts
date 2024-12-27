import OpenAI from "openai";
import * as cheerio from "cheerio";
import fetch from "node-fetch";
import type { Response } from "node-fetch";

if (!process.env.OPENAI_API_KEY) {
  throw new Error("OPENAI_API_KEY is not set");
}

// the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export interface AIAnalysis {
  title: string;
  description: string;
  tags: string[];
  isLandingPage?: boolean;
  mainTopic?: string;
  metadata?: {
    author?: string;
    publishDate?: string;
    lastModified?: string;
    contentType?: string;
    mainImage?: string;
    wordCount?: number;
  };
}

interface PageContent {
  url: string;
  title: string;
  description: string;
  content: string;
  links: string[];
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
  private static readonly RETRY_DELAY = 2000;

  private static async delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private static normalizeUrl(url: string): string {
    try {
      // Handle case where URL starts with www.
      if (url.startsWith('www.')) {
        url = 'https://' + url;
      }
      // Handle case where URL starts with http:// by upgrading to https://
      if (url.startsWith('http://')) {
        url = 'https://' + url.slice(7);
      }
      // Add https:// if no protocol is present
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
      $('script, style, nav, footer, iframe, noscript, header').remove();
      $('.cookie-banner, .advertisement, .social-media').remove();
      $('[class*="cookie"], [class*="banner"], [class*="popup"], [class*="modal"]').remove();
      $('[role="complementary"], [role="banner"]').remove();

      // Extract key content with better fallbacks
      const title = $('meta[property="og:title"]').attr('content')?.trim() ||
                   $('title').text().trim() ||
                   $('h1').first().text().trim() ||
                   'Untitled Page';

      const metaDescription = $('meta[property="og:description"]').attr('content')?.trim() ||
                            $('meta[name="description"]').attr('content')?.trim() ||
                            '';

      // Identify main content area
      const contentSelectors = [
        'article',
        '[role="main"]',
        'main',
        '#content',
        '.content',
        '.post-content',
        '.article-content'
      ];

      let mainContent = '';
      for (const selector of contentSelectors) {
        const element = $(selector).first();
        if (element.length) {
          mainContent = element.text().trim();
          break;
        }
      }

      // Fallback to body if no main content found
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
                $('[rel="author"]').first().text() ||
                $('.author').first().text(),
        publishDate: $('meta[property="article:published_time"]').attr('content') ||
                    $('time[pubdate]').attr('datetime') ||
                    $('[itemprop="datePublished"]').attr('content'),
        lastModified: $('meta[property="article:modified_time"]').attr('content') ||
                     $('[itemprop="dateModified"]').attr('content'),
        mainImage: $('meta[property="og:image"]').attr('content') ||
                  $('meta[name="twitter:image"]').attr('content') ||
                  $('article img').first().attr('src'),
        wordCount: mainContent.split(/\s+/).length
      };

      // Determine content type
      let type: 'webpage' | 'video' | 'article' | 'product' = 'webpage';
      if ($('[itemtype*="Product"]').length || $('.price').length || $('#price').length) {
        type = 'product';
      } else if ($('article').length || $('[itemtype*="Article"]').length || $('.post').length) {
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
          .slice(0, 2000),
        links: [],
        type,
        metadata
      };

    } catch (error) {
      console.error(`[Analysis] Error fetching ${url}:`, error);

      if (retries < this.MAX_RETRIES) {
        console.warn(`[Analysis] Retrying ${url} (attempt ${retries + 1})`);
        await this.delay(this.RETRY_DELAY * Math.pow(2, retries));
        return this.fetchWithRetry(url, retries + 1);
      }

      throw new Error(`Failed to fetch page: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  static async analyzeUrl(url: string): Promise<AIAnalysis> {
    try {
      const normalizedUrl = this.normalizeUrl(url);
      console.log(`[Analysis] Starting analysis of: ${normalizedUrl}`);

      const pageContent = await this.fetchWithRetry(normalizedUrl);
      console.log(`[Analysis] Successfully fetched page content`);

      const response = await openai.chat.completions.create({
        model: "gpt-4o",
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: `You are an expert content analyzer. Your task is to analyze web content and provide detailed, accurate analysis focusing on the main purpose and value of the page. Always return a complete analysis with all requested fields.`
          },
          {
            role: "user",
            content: `Analyze this web content:

URL: ${pageContent.url}
Title: ${pageContent.title}
Type: ${pageContent.type}
Content: ${pageContent.content}

Return a JSON object with these fields:
{
  "title": "Clear, concise title (max 60 chars)",
  "description": "Detailed summary of the content (max 200 chars)",
  "tags": ["3-5 relevant tags"],
  "isLandingPage": boolean,
  "mainTopic": "primary topic or purpose"
}`
          },
        ],
        temperature: 0.3,
        max_tokens: 800,
      });

      const result = response.choices[0]?.message?.content;
      if (!result) {
        throw new Error("No response from OpenAI");
      }

      console.log(`[Analysis] Raw analysis result:`, result);
      const analysis = JSON.parse(result) as {
        title: string;
        description: string;
        tags: string[];
        isLandingPage: boolean;
        mainTopic: string;
      };

      return {
        title: analysis.title.slice(0, 60),
        description: analysis.description.slice(0, 200),
        tags: analysis.tags.slice(0, 5).map((tag: string) => tag.toLowerCase()),
        isLandingPage: analysis.isLandingPage,
        mainTopic: analysis.mainTopic,
        metadata: pageContent.metadata
      };
    } catch (error) {
      console.error('[Analysis] Error in analyzeUrl:', error);

      // Create meaningful fallback analysis
      try {
        const urlParts = new URL(url);
        return {
          title: urlParts.hostname,
          description: `Website at ${urlParts.hostname}${urlParts.pathname} - ${error instanceof Error ? error.message : 'Access error'}`,
          tags: ['error', 'unavailable'],
          isLandingPage: false,
          mainTopic: 'unknown'
        };
      } catch {
        return {
          title: 'Invalid URL',
          description: 'The provided URL could not be processed',
          tags: ['error', 'invalid'],
          isLandingPage: false,
          mainTopic: 'unknown'
        };
      }
    }
  }
}