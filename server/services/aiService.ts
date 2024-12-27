import OpenAI from "openai";
import * as cheerio from "cheerio";
import fetch from "node-fetch";

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
}

interface PageContent {
  url: string;
  title: string;
  description: string;
  content: string;
  links: string[];
  type?: 'webpage' | 'video' | 'article';
}

export class AIService {
  private static readonly MAX_PAGES = 3;
  private static readonly MAX_DEPTH = 1;
  private static readonly MAX_RETRIES = 3;
  private static readonly RETRY_DELAY = 2000; // 2 seconds
  private static visitedUrls = new Set<string>();

  private static async delay(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private static isValidUrl(urlString: string): boolean {
    try {
      const url = new URL(urlString);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
      return false;
    }
  }

  private static normalizeUrl(url: string): string {
    try {
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

  private static isSameOrigin(baseUrl: string, urlToCheck: string): boolean {
    try {
      const base = new URL(baseUrl);
      const check = new URL(urlToCheck);
      return base.origin === check.origin;
    } catch {
      return false;
    }
  }

  private static getContentType(url: string): 'webpage' | 'video' | 'article' {
    const urlObj = new URL(url);
    if (urlObj.hostname.includes('youtube.com') || urlObj.hostname.includes('youtu.be')) {
      return 'video';
    }
    // Add more video platforms as needed
    if (urlObj.hostname.includes('vimeo.com') || urlObj.hostname.includes('dailymotion.com')) {
      return 'video';
    }
    // Check for common article/blog platforms
    if (urlObj.hostname.includes('medium.com') || urlObj.hostname.includes('wordpress.com')) {
      return 'article';
    }
    return 'webpage';
  }

  private static async fetchWithRetry(url: string, retries = 0): Promise<PageContent> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

      const contentType = this.getContentType(url);
      if (contentType === 'video') {
        clearTimeout(timeoutId);
        return this.handleVideoContent(url);
      }

      const isHttps = url.startsWith('https://');
      const agent = isHttps 
        ? new (await import('node:https')).Agent({ rejectUnauthorized: false })
        : new (await import('node:http')).Agent();

      const response = await fetch(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; BookmarkAnalyzer/1.0)',
          'Accept-Language': '*'
        },
        signal: controller.signal,
        agent
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const html = await response.text();
      const $ = cheerio.load(html);

      // Remove non-content elements
      $('script').remove();
      $('style').remove();
      $('nav').remove();
      $('footer').remove();
      $('iframe').remove();
      $('noscript').remove();
      $('header').remove();
      $('.cookie-banner').remove();
      $('.advertisement').remove();
      $('.social-media').remove();

      // Extract key content with better fallbacks
      const title = $('title').text().trim() || 
                   $('meta[property="og:title"]').attr('content')?.trim() || 
                   $('h1').first().text().trim() || 
                   'Untitled Page';

      const metaDescription = $('meta[name="description"]').attr('content')?.trim() || 
                            $('meta[property="og:description"]').attr('content')?.trim() || '';

      const mainContent = $('main, article, #content, .content, [role="main"]').text() || 
                         $('body').clone().children('nav,header,footer,aside').remove().end().text();

      // Extract navigation links for deeper crawling
      const links = $('a[href]')
        .map((_, el) => $(el).attr('href'))
        .get()
        .filter(href => href && !href.startsWith('#') && !href.startsWith('javascript:'))
        .map(href => {
          try {
            return new URL(href, url).toString();
          } catch {
            return null;
          }
        })
        .filter((url): url is string => url !== null && this.isSameOrigin(url, url));

      return {
        url,
        title,
        description: metaDescription,
        content: [title, metaDescription, mainContent]
          .filter(Boolean)
          .join('\n\n')
          .replace(/\s+/g, ' ')
          .trim()
          .slice(0, 1000),
        links: Array.from(new Set(links)),
        type: contentType
      };
    } catch (error) {
      // Don't retry DNS failures
      if (error instanceof Error && 
          (error as any).code === 'ENOTFOUND') {
        throw new Error(`Domain not found: ${url}`);
      }
      
      if (retries < this.MAX_RETRIES) {
        if (error instanceof Error && error.name === 'AbortError') {
          console.warn(`Request timeout for ${url}, attempt ${retries + 1}`);
        } else {
          console.warn(`Retry ${retries + 1} for ${url}:`, error);
        }
        await this.delay(this.RETRY_DELAY * Math.pow(2, retries));
        return this.fetchWithRetry(url, retries + 1);
      }
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timed out after ${this.MAX_RETRIES} attempts: ${url}`);
      }
      throw new Error(`Failed to fetch page after ${this.MAX_RETRIES} retries: ${url}`);
    }
  }

  private static async handleVideoContent(url: string): Promise<PageContent> {
    // Extract video ID and basic info from URL
    const urlObj = new URL(url);
    let videoId = '';
    let platform = '';

    if (urlObj.hostname.includes('youtube.com')) {
      videoId = urlObj.searchParams.get('v') || '';
      platform = 'YouTube';
    } else if (urlObj.hostname === 'youtu.be') {
      videoId = urlObj.pathname.slice(1);
      platform = 'YouTube';
    }
    // Add more video platforms as needed

    return {
      url,
      title: `${platform} Video`,
      description: `A video hosted on ${platform}`,
      content: `This is a ${platform} video with ID: ${videoId}`,
      links: [],
      type: 'video'
    };
  }

  private static async crawlWebsite(startUrl: string): Promise<PageContent[]> {
    const pages: PageContent[] = [];
    const queue: { url: string; depth: number }[] = [{ url: startUrl, depth: 0 }];
    this.visitedUrls.clear();

    while (queue.length > 0 && pages.length < this.MAX_PAGES) {
      const { url, depth } = queue.shift()!;

      if (this.visitedUrls.has(url) || depth > this.MAX_DEPTH) {
        continue;
      }

      try {
        const pageContent = await this.fetchWithRetry(url);
        pages.push(pageContent);
        this.visitedUrls.add(url);

        if (depth < this.MAX_DEPTH) {
          const newLinks = pageContent.links
            .filter(link => !this.visitedUrls.has(link))
            .slice(0, 5);

          for (const link of newLinks) {
            queue.push({ url: link, depth: depth + 1 });
          }
        }

        await this.delay(1000); // Rate limiting
      } catch (error) {
        console.error(`Error crawling ${url}:`, error);
        continue;
      }
    }

    return pages;
  }

  private static async analyzeWithRetry(startUrl: string, pages: PageContent[], retries = 0): Promise<AIAnalysis> {
    try {
      const response = await openai.chat.completions.create({
        model: "gpt-4o",
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: "You are a website analyzer specializing in identifying landing pages and general websites. Provide detailed analysis of content focus and target audience."
          },
          {
            role: "user",
            content: `Analyze these pages from ${startUrl} and determine if it's a landing page or general website:

${pages.map(page => `
URL: ${page.url}
Title: ${page.title}
Content: ${page.content.slice(0, 500)}
Type: ${page.type || 'webpage'}
---`).join('\n')}

Return a JSON object with:
- title: Clear, concise website purpose (max 60 chars)
- description: If landing page, specific focus and call-to-action. If general site, overview of main topics and purpose. (max 200 chars)
- tags: 3-5 relevant tags for content type, purpose, and target audience
- isLandingPage: boolean indicating if this is a focused landing page
- mainTopic: primary topic or purpose if landing page, "general" if multi-topic site

Use this structure:
{
  "title": string,
  "description": string,
  "tags": string[],
  "isLandingPage": boolean,
  "mainTopic": string
}`
          },
        ],
        temperature: 0.3,
        max_tokens: 500,
      });

      const result = response.choices[0]?.message?.content;
      if (!result) {
        throw new Error("No response from OpenAI");
      }

      const analysis = JSON.parse(result);

      if (!analysis.title || !analysis.description || !Array.isArray(analysis.tags)) {
        throw new Error("Invalid response format from OpenAI");
      }

      return {
        title: analysis.title.slice(0, 60),
        description: analysis.description.slice(0, 200),
        tags: analysis.tags.slice(0, 5).map((tag: string) => tag.toLowerCase()),
      };
    } catch (error) {
      if (retries < this.MAX_RETRIES && 
          (error instanceof Error && error.message.includes('rate limit'))) {
        console.warn(`Retry ${retries + 1} for analysis:`, error);
        await this.delay(this.RETRY_DELAY * Math.pow(2, retries));
        return this.analyzeWithRetry(startUrl, pages, retries + 1);
      }
      throw error;
    }
  }

  static async analyzeUrl(url: string): Promise<AIAnalysis> {
    try {
      const normalizedUrl = this.normalizeUrl(url);
      if (!this.isValidUrl(normalizedUrl)) {
        throw new Error('Invalid URL format');
      }

      console.log(`Starting analysis of: ${normalizedUrl}`);
      const pages = await this.crawlWebsite(normalizedUrl);

      if (pages.length === 0) {
        throw new Error('Failed to fetch any pages from the website');
      }

      console.log(`Successfully crawled ${pages.length} pages from ${normalizedUrl}`);
      return await this.analyzeWithRetry(normalizedUrl, pages);
    } catch (error) {
      console.error('Error in analyzeUrl:', error);

      // Return a structured error response that can be stored in the database
      if (error instanceof Error) {
        if (error.message.includes('Invalid URL')) {
          throw new Error('Invalid URL format: Please provide a valid http:// or https:// URL');
        } else if (error.message.includes('rate limit')) {
          throw new Error('Service temporarily unavailable: Rate limit exceeded, please try again later');
        } else if (error.message.includes('fetch') || error.message.includes('ECONNREFUSED')) {
          throw new Error('Website unreachable: The URL provided could not be accessed');
        }
      }
      throw new Error('Analysis failed: Unable to process the website content');
    }
  }
}