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
  isLandingPage?: boolean;
  mainTopic?: string;
  screenshot?: string;
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
  screenshot?: string;
  metadata?: {
    author?: string;
    publishDate?: string;
    lastModified?: string;
    mainImage?: string;
    wordCount?: number;
  };
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

  private static getContentType(url: string, $: cheerio.CheerioAPI): 'webpage' | 'video' | 'article' | 'product' {
    const urlObj = new URL(url);

    // Check for video platforms
    if (urlObj.hostname.includes('youtube.com') ||
        urlObj.hostname.includes('youtu.be') ||
        urlObj.hostname.includes('vimeo.com') ||
        urlObj.hostname.includes('dailymotion.com')) {
      return 'video';
    }

    // Check for product pages
    const priceSelectors = ['[itemprop="price"]', '.price', '#price', '[data-price]'];
    const hasPrice = priceSelectors.some(selector => $(selector).length > 0);
    if (hasPrice || $('[itemtype*="Product"]').length > 0) {
      return 'product';
    }

    // Check for articles
    const articleIndicators = [
      'article',
      '[itemtype*="Article"]',
      '.post',
      '.blog-post',
      '[class*="article"]',
      'time',
      '.published',
      '.author'
    ];
    const isArticle = articleIndicators.some(selector => $(selector).length > 0) ||
                     urlObj.hostname.includes('medium.com') ||
                     urlObj.hostname.includes('wordpress.com');

    return isArticle ? 'article' : 'webpage';
  }

  private static extractMetadata($: cheerio.CheerioAPI): PageContent['metadata'] {
    const metadata: PageContent['metadata'] = {};

    // Extract author
    metadata.author = $('meta[name="author"]').attr('content') ||
                     $('[rel="author"]').first().text() ||
                     $('.author').first().text() ||
                     undefined;

    // Extract dates
    metadata.publishDate = $('meta[property="article:published_time"]').attr('content') ||
                          $('time[pubdate]').attr('datetime') ||
                          $('[itemprop="datePublished"]').attr('content') ||
                          undefined;

    metadata.lastModified = $('meta[property="article:modified_time"]').attr('content') ||
                           $('[itemprop="dateModified"]').attr('content') ||
                           undefined;

    // Extract main image
    metadata.mainImage = $('meta[property="og:image"]').attr('content') ||
                        $('meta[name="twitter:image"]').attr('content') ||
                        $('article img').first().attr('src') ||
                        undefined;

    // Calculate word count
    const text = $('body').text();
    metadata.wordCount = text.split(/\s+/).length;

    return metadata;
  }

  private static async fetchWithRetry(url: string, retries = 0): Promise<PageContent> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      console.log(`[Analysis] Attempting to fetch ${url} (attempt ${retries + 1})`);

      // Take screenshot using puppeteer
      const puppeteer = await import('puppeteer');
      const browser = await puppeteer.launch({ 
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
        headless: 'new',
        executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined
      });

      try {
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');

        // Set viewport for better screenshots
        await page.setViewport({
          width: 1920,
          height: 1080,
          deviceScaleFactor: 1,
        });

        // Navigate with timeout and error handling
        try {
          const response = await Promise.race([
            page.goto(url, { 
              waitUntil: ['networkidle0', 'domcontentloaded'],
              timeout: 30000
            }),
            new Promise((_, reject) => 
              setTimeout(() => reject(new Error('Navigation timeout')), 30000)
            )
          ]);

          if (!response) {
            throw new Error('unreachable');
          }

          // Handle HTTP errors
          if (response.status() >= 400) {
            throw new Error(`HTTP ${response.status()}: ${response.statusText()}`);
          }
        } catch (error) {
          throw new Error('unreachable');
        }

        // Wait for content to load
        await page.evaluate(() => new Promise(resolve => {
          let totalHeight = 0;
          const distance = 100;
          const timer = setInterval(() => {
            const scrollHeight = document.body.scrollHeight;
            window.scrollBy(0, distance);
            totalHeight += distance;
            if(totalHeight >= scrollHeight) {
              clearInterval(timer);
              resolve(true);
            }
          }, 100);
        }));

        // Scroll back to top
        await page.scrollTo(0, 0);

        // Take full page screenshot
        const screenshot = await page.screenshot({ 
          encoding: 'base64',
          fullPage: true,
          type: 'jpeg',
          quality: 80
        });

        // Get HTML content
        const html = await page.content();
        clearTimeout(timeoutId);

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
        $('[class*="cookie"]').remove();
        $('[class*="banner"]').remove();
        $('[class*="popup"]').remove();
        $('[class*="modal"]').remove();
        $('[role="complementary"]').remove();
        $('[role="banner"]').remove();

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

        const contentType = this.getContentType(url, $);
        const metadata = this.extractMetadata($);

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
          links: Array.from(new Set(links)),
          type: contentType,
          screenshot: screenshot.toString(),
          metadata
        };
      } finally {
        await browser.close();
      }
    } catch (error) {
      console.error(`[Analysis] Error fetching ${url}:`, error);

      // Don't retry certain errors
      if (error instanceof Error && 
          (error.message === 'unreachable' || 
           (error as any).code === 'ENOTFOUND')) {
        throw new Error(`Website unreachable: ${url}`);
      }

      if (retries < this.MAX_RETRIES) {
        console.warn(`[Analysis] Retrying ${url} (attempt ${retries + 1})`);
        await this.delay(this.RETRY_DELAY * Math.pow(2, retries));
        return this.fetchWithRetry(url, retries + 1);
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

    // Try to fetch video thumbnail
    let thumbnailUrl;
    if (platform === 'YouTube' && videoId) {
      thumbnailUrl = `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
    }

    return {
      url,
      title: `${platform} Video`,
      description: `A video hosted on ${platform}`,
      content: `This is a ${platform} video with ID: ${videoId}`,
      links: [],
      type: 'video',
      metadata: {
        mainImage: thumbnailUrl
      }
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
      const mainPage = pages[0]; // Use the first page as the main one for analysis
      const response = await openai.chat.completions.create({
        model: "gpt-4o",
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: `You are an expert website analyzer with the following capabilities:
1. Identify the type of website and its primary purpose
2. Determine the target audience and content quality
3. Extract key themes and topics
4. Evaluate content credibility and relevance
5. Generate meaningful descriptions even for partially accessible content

Consider these content types:
- Article: Focus on author, publish date, and key points
- Product: Highlight features, pricing, and target market
- Video: Describe the platform and content type
- General webpage: Focus on main purpose and user value`
          },
          {
            role: "user",
            content: `Analyze these pages from ${startUrl} and provide a comprehensive analysis:

Main page type: ${mainPage.type}
Metadata: ${JSON.stringify(mainPage.metadata, null, 2)}

Available content:
${pages.map(page => `
URL: ${page.url}
Title: ${page.title}
Type: ${page.type}
Content: ${page.content.slice(0, 500)}
---`).join('\n')}

Return a JSON object with:
- title: Clear, concise website purpose (max 60 chars)
- description: Detailed analysis based on content type (max 200 chars)
- tags: 3-5 relevant tags for content type, purpose, and target audience
- isLandingPage: boolean indicating if this is a focused landing page
- mainTopic: primary topic or purpose
- metadata: include relevant metadata from the page`
          },
        ],
        temperature: 0.3,
        max_tokens: 800,
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
        isLandingPage: analysis.isLandingPage,
        mainTopic: analysis.mainTopic,
        screenshot: mainPage.screenshot,
        metadata: mainPage.metadata
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

      console.log(`[Analysis] Starting analysis of: ${normalizedUrl}`);
      const pages = await this.crawlWebsite(normalizedUrl);

      console.log(`[Analysis] Crawled ${pages.length} pages from ${normalizedUrl}`);

      if (!pages.length) {
        // Create fallback analysis from URL
        const urlParts = new URL(normalizedUrl);
        return {
          title: urlParts.hostname,
          description: `Website at ${urlParts.hostname}${urlParts.pathname} - Currently unavailable or restricted access`,
          tags: ['archived', 'unavailable'],
          isLandingPage: false,
          mainTopic: 'unknown'
        };
      }

      return await this.analyzeWithRetry(normalizedUrl, pages);
    } catch (error) {
      console.error('[Analysis] Error in analyzeUrl:', error);

      // Create meaningful fallback analysis
      try {
        const urlParts = new URL(url);
        return {
          title: urlParts.hostname,
          description: `Website at ${urlParts.hostname} - ${error instanceof Error ? error.message : 'Access error'}`,
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