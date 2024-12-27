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
}

export class AIService {
  private static readonly MAX_PAGES = 3; // Reduced from 5 to optimize for mini model
  private static readonly MAX_DEPTH = 1; // Reduced from 2 to optimize for mini model
  private static visitedUrls = new Set<string>();

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
      const parsedUrl = new URL(url);
      return parsedUrl.toString().replace(/\/$/, '');
    } catch {
      if (!url.startsWith('http')) {
        return this.normalizeUrl(`https://${url}`);
      }
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

  private static async fetchPage(url: string): Promise<PageContent> {
    try {
      const response = await fetch(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; BookmarkAnalyzer/1.0)',
          'Accept-Language': '*'
        }
      });

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
                   $('h1').first().text().trim() || '';

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
          .slice(0, 1000), // Reduced content length for mini model
        links: Array.from(new Set(links))
      };
    } catch (error) {
      console.error(`Error fetching ${url}:`, error);
      throw new Error(`Failed to fetch page: ${url}`);
    }
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
        const pageContent = await this.fetchPage(url);
        pages.push(pageContent);
        this.visitedUrls.add(url);

        if (depth < this.MAX_DEPTH) {
          const newLinks = pageContent.links
            .filter(link => !this.visitedUrls.has(link))
            .slice(0, 5); // Reduced from 10 for mini model

          for (const link of newLinks) {
            queue.push({ url: link, depth: depth + 1 });
          }
        }

        await new Promise(resolve => setTimeout(resolve, 1000));
      } catch (error) {
        console.error(`Error crawling ${url}:`, error);
        continue;
      }
    }

    return pages;
  }

  private static async analyzeContent(startUrl: string, pages: PageContent[]): Promise<AIAnalysis> {
    try {
      const response = await openai.chat.completions.create({
        model: "gpt-4o", // Using the newer GPT-4o model
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: "You are a website analyzer. Analyze the pages and provide a concise summary of the website's purpose and key features. Keep responses brief but informative."
          },
          {
            role: "user",
            content: `Analyze these pages from ${startUrl} and provide insights:

${pages.map(page => `
URL: ${page.url}
Title: ${page.title}
Content: ${page.content.slice(0, 500)}
---`).join('\n')}

Return a JSON object with:
- title: Clear, concise website purpose (max 60 chars)
- description: Website's purpose and target audience (max 200 chars)
- tags: 3-5 relevant tags for purpose and features

Use this structure:
{
  "title": string,
  "description": string,
  "tags": string[]
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
        console.error('Invalid OpenAI response format:', result);
        throw new Error("Invalid response format");
      }

      return {
        title: analysis.title.slice(0, 60),
        description: analysis.description.slice(0, 200),
        tags: analysis.tags.slice(0, 5).map((tag: string) => tag.toLowerCase()),
      };
    } catch (error) {
      console.error('Error analyzing content:', error);
      throw new Error('Failed to analyze content');
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
      return await this.analyzeContent(normalizedUrl, pages);
    } catch (error) {
      console.error('Error in analyzeUrl:', error);
      throw new Error('Failed to analyze URL');
    }
  }
}