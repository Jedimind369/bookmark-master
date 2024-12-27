import OpenAI from "openai";
import * as cheerio from "cheerio";
import fetch from "node-fetch";

if (!process.env.OPENAI_API_KEY) {
  throw new Error("OPENAI_API_KEY is not set");
}

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
  private static readonly MAX_PAGES = 5;
  private static readonly MAX_DEPTH = 2;
  private static visitedUrls = new Set<string>();

  private static isValidUrl(urlString: string): boolean {
    try {
      const url = new URL(urlString);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
      return false;
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
      const response = await fetch(url);
      const html = await response.text();
      const $ = cheerio.load(html);

      // Remove non-content elements
      $('script').remove();
      $('style').remove();
      $('nav').remove();
      $('footer').remove();
      $('iframe').remove();
      $('noscript').remove();

      // Extract key content
      const title = $('title').text().trim() || '';
      const metaDescription = $('meta[name="description"]').attr('content')?.trim() || '';
      const h1 = $('h1').first().text().trim();
      const mainContent = $('main, article, #content, .content').text() || $('body').text();

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
        content: [
          title,
          h1,
          metaDescription,
          mainContent
        ].filter(Boolean).join('\n\n'),
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

        // Add child pages to queue
        if (depth < this.MAX_DEPTH) {
          for (const link of pageContent.links) {
            if (!this.visitedUrls.has(link)) {
              queue.push({ url: link, depth: depth + 1 });
            }
          }
        }

        // Add a small delay between requests
        await new Promise(resolve => setTimeout(resolve, 500));
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
        model: "gpt-3.5-turbo",
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: "You are a specialized website analyzer. Your task is to analyze multiple pages from a website and provide a comprehensive understanding of the website's true purpose, main features, and target audience. Provide all output in English, regardless of the original language.",
          },
          {
            role: "user",
            content: `Analyze these pages from the website ${startUrl} and provide a comprehensive understanding:

${pages.map(page => `
URL: ${page.url}
Title: ${page.title}
Description: ${page.description}
Content: ${page.content.slice(0, 1000)}
---`).join('\n')}

Return a JSON object with:
- title: A clear, concise title that describes the website's main purpose (max 60 chars)
- description: A comprehensive summary of the website's purpose, features, and target audience (max 300 chars)
- tags: 5-7 relevant tags, including purpose, industry, target audience, and key features

Use this exact JSON structure:
{
  "title": "string",
  "description": "string",
  "tags": ["string"]
}`
          },
        ],
        temperature: 0.3,
        max_tokens: 1000,
      });

      const result = response.choices[0]?.message?.content;
      if (!result) {
        throw new Error("No response from OpenAI");
      }

      const analysis = JSON.parse(result);

      // Validate and clean up the response
      if (!analysis.title || !analysis.description || !Array.isArray(analysis.tags)) {
        console.error('Invalid OpenAI response format:', result);
        throw new Error("Invalid response format");
      }

      return {
        title: analysis.title.slice(0, 60),
        description: analysis.description.slice(0, 300),
        tags: analysis.tags.slice(0, 7).map(tag => tag.toLowerCase()),
      };
    } catch (error) {
      console.error('Error analyzing content:', error);
      throw new Error('Failed to analyze content');
    }
  }

  static async analyzeUrl(url: string): Promise<AIAnalysis> {
    try {
      if (!this.isValidUrl(url)) {
        throw new Error('Invalid URL format');
      }

      const pages = await this.crawlWebsite(url);
      if (pages.length === 0) {
        throw new Error('Failed to fetch any pages from the website');
      }

      return await this.analyzeContent(url, pages);
    } catch (error) {
      console.error('Error in analyzeUrl:', error);
      throw new Error('Failed to analyze URL');
    }
  }
}