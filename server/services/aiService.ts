import Anthropic from '@anthropic-ai/sdk';
import * as cheerio from 'cheerio';
import fetch from 'node-fetch';
import type { Response } from 'node-fetch';
import fs from 'fs/promises';
import path from 'path';
import { YouTubeService } from './youtubeService';

// Verify API key is set
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
if (!ANTHROPIC_API_KEY) {
  throw new Error("ANTHROPIC_API_KEY is not set");
}

// the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
const anthropic = new Anthropic({
  apiKey: ANTHROPIC_API_KEY
});

// Create debug directory if it doesn't exist
const debugDir = path.join(process.cwd(), 'debug');
fs.mkdir(debugDir).catch(() => {
  // Ignore error if directory already exists
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

  private static async analyzeVideoContent(pageContent: PageContent): Promise<AIAnalysis> {
    try {
      console.log(`[Video Analysis] Starting analysis for: ${pageContent.url}`);

      // Fetch complete video content for YouTube videos
      let videoContent = pageContent.content;
      let videoMetadata = pageContent.metadata || {};

      if (pageContent.url.includes('youtube.com') || pageContent.url.includes('youtu.be')) {
        const youtubeContent = await YouTubeService.getVideoContent(pageContent.url);
        if (youtubeContent) {
          videoContent = `
Title: ${youtubeContent.title}
Author: ${youtubeContent.author}
Published: ${youtubeContent.publishDate}
Description: ${youtubeContent.description}
Full Transcript: ${youtubeContent.transcript}
`.trim();

          videoMetadata = {
            ...videoMetadata,
            author: youtubeContent.author,
            publishDate: youtubeContent.publishDate
          };
        }
      }

      const message = await anthropic.messages.create({
        model: "claude-3-5-sonnet-20241022",
        max_tokens: 4000,
        temperature: 0.3,
        messages: [{
          role: "user",
          content: `Analyze this video content in extreme detail. Extract maximum value from the transcript and description to create a comprehensive analysis:

Title: ${pageContent.title}
Description: ${pageContent.description}
Author: ${pageContent.metadata?.author || 'Unknown'}
Type: ${pageContent.type}
Full Content: ${videoContent}

Your task is to provide an extremely detailed analysis that captures the depth and nuance of the video content.
Return a detailed analysis in this exact JSON structure:
{
  "title": "Write a complete, engaging title (60-100 characters) that accurately represents the video content and includes key topics",
  "description": "Write a comprehensive, multi-paragraph description (MINIMUM 5 detailed paragraphs) that MUST include:
    1. Overview: Main purpose, target audience, and context of the video
    2. Key Arguments: Present the main arguments, claims, or demonstrations in detail
    3. Supporting Evidence: Document specific examples, case studies, statistics, or data discussed
    4. Analysis: Evaluate the quality and credibility of the content
    5. Value Proposition: Explain why this content is valuable and what viewers will learn
    Include exact quotes from the transcript when possible to support key points",
  "tags": ["10-15 specific, relevant tags that accurately capture:
    - Main topic and all subtopics
    - Content type and format
    - Industry or field
    - Technical terms and methodologies
    - Target audience
    - Related concepts and themes"],
  "contentQuality": {
    "relevance": "Score 0-1 based on topic relevance and audience fit",
    "informativeness": "Score 0-1 based on depth and usefulness of information",
    "credibility": "Score 0-1 based on evidence and expertise shown",
    "overallScore": "Average of the above scores"
  },
  "mainTopics": ["4-6 main topics covered in detail"],
  "recommendations": {
    "improvedTitle": "Enhanced title emphasizing value proposition",
    "improvedDescription": "Alternative description focusing on unique insights and practical applications",
    "suggestedTags": ["5-7 additional tags focusing on specific concepts and applications"]
  }
}`
        }]
      });

      // Get content from the new Anthropic API response format
      const content = message.content[0].type === 'text' ? message.content[0].text : '';
      if (!content) {
        throw new Error('No content in AI response');
      }

      // Save response for debugging
      await this.saveDebugInfo(pageContent.url, { aiResponse: content }, 'video_analysis');

      try {
        const analysis = JSON.parse(content);

        // Validate and enhance the analysis
        if (!analysis.title || !analysis.description || !Array.isArray(analysis.tags)) {
          throw new Error('Invalid response structure');
        }

        // Combine and deduplicate tags
        const combinedTags = Array.from(new Set([
          ...(analysis.tags || []),
          ...(analysis.recommendations?.suggestedTags || []),
          'video',
          pageContent.type,
          ...this.extractKeywordsFromTranscript(videoContent)
        ])).slice(0, 15);

        return {
          title: analysis.title || analysis.recommendations?.improvedTitle || pageContent.title,
          description: analysis.description || analysis.recommendations?.improvedDescription || pageContent.description,
          tags: combinedTags.map(tag => tag.toLowerCase()),
          contentQuality: {
            relevance: Math.max(0, Math.min(1, analysis.contentQuality?.relevance || 0.8)),
            informativeness: Math.max(0, Math.min(1, analysis.contentQuality?.informativeness || 0.8)),
            credibility: Math.max(0, Math.min(1, analysis.contentQuality?.credibility || 0.8)),
            overallScore: Math.max(0, Math.min(1, analysis.contentQuality?.overallScore || 0.8))
          },
          mainTopics: (analysis.mainTopics || ['video content']).slice(0, 6),
          recommendations: {
            improvedTitle: analysis.recommendations?.improvedTitle,
            improvedDescription: analysis.recommendations?.improvedDescription,
            suggestedTags: analysis.recommendations?.suggestedTags
          },
          metadata: {
            ...videoMetadata,
            analysisAttempts: 1
          }
        };
      } catch (parseError) {
        console.error('[Video Analysis] Failed to parse AI response:', parseError, 'Raw content:', content);
        return this.createFallbackAnalysis(pageContent, 'Failed to parse AI response');
      }
    } catch (error) {
      console.error('[Video Analysis] Error:', error);
      return this.createFallbackAnalysis(pageContent, error instanceof Error ? error.message : 'Unknown error');
    }
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

  private static createFallbackAnalysis(pageContent: PageContent, errorReason: string): AIAnalysis {
    console.log('[Analysis] Creating fallback analysis due to:', errorReason);

    // Extract video ID and other metadata for better fallback content
    const videoId = pageContent.url.includes('youtube.com/watch?v=')
      ? new URL(pageContent.url).searchParams.get('v')
      : pageContent.url.split('/').pop();

    const creator = pageContent.metadata?.author || 'content creator';
    const defaultDescription = `This video content was created by ${creator}. ` +
      `The video covers important topics and information that may be valuable to viewers. ` +
      `Due to technical limitations, a detailed analysis is currently unavailable. ` +
      `The original title of the video is "${pageContent.title}". ` +
      `For the most accurate information, please view the video directly.`;

    return {
      title: pageContent.title || `Video Content: ${videoId || 'Untitled'}`,
      description: pageContent.description || defaultDescription,
      tags: [
        'video',
        'content',
        'online-media',
        'digital-content',
        'educational'
      ],
      contentQuality: {
        relevance: 0.8,
        informativeness: 0.8,
        credibility: 0.8,
        overallScore: 0.8
      },
      mainTopics: ['video content', 'digital media', 'online education'],
      metadata: {
        ...pageContent.metadata,
        analysisAttempts: 1,
        error: errorReason
      }
    };
  }

  private static async analyzeWebContent(pageContent: PageContent): Promise<AIAnalysis> {
    // Truncate content to avoid token limit
    const truncatedContent = pageContent.content.slice(0, 1500);

    const message = await anthropic.messages.create({
      model: "claude-3-5-sonnet-20241022",
      max_tokens: 1024,
      temperature: 0.3,
      messages: [{
        role: "user",
        content: `Analyze this webpage content briefly:
URL: ${pageContent.url}
Title: ${pageContent.title.slice(0, 100)}
Type: ${pageContent.type}
Description: ${pageContent.description.slice(0, 200)}
Content Preview: ${truncatedContent}

Provide a concise JSON analysis with:
{
  "title": "<60 char title>",
  "description": "<160 char summary>",
  "tags": ["3-5 tags"],
  "contentQuality": {
    "relevance": 0-1,
    "informativeness": 0-1,
    "credibility": 0-1,
    "overallScore": 0-1
  },
  "mainTopics": ["2-3 topics"],
  "recommendations": {
    "improvedTitle": "optional better title",
    "improvedDescription": "optional better description",
    "suggestedTags": ["optional better tags"]
  }
}`
      }]
    });

    // Get content from the new Anthropic API response format
    const content = message.content[0].type === 'text' ? message.content[0].text : '';
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