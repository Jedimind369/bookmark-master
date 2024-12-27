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

export class AIService {
  static async fetchUrlContent(url: string): Promise<string> {
    try {
      const response = await fetch(url);
      const html = await response.text();
      const $ = cheerio.load(html);

      // Remove scripts, styles, and other non-content elements
      $('script').remove();
      $('style').remove();
      $('nav').remove();
      $('footer').remove();

      // Get the main content
      const title = $('title').text() || '';
      const description = $('meta[name="description"]').attr('content') || '';
      const mainContent = $('main, article, #content, .content').text() || $('body').text();

      // Combine and clean the text
      const content = `${title}\n${description}\n${mainContent}`
        .replace(/\s+/g, ' ')
        .trim()
        .slice(0, 1500); // Limit content length

      return content;
    } catch (error) {
      console.error('Error fetching URL content:', error);
      throw new Error('Failed to fetch URL content');
    }
  }

  static async analyzeContent(url: string, content: string): Promise<AIAnalysis> {
    try {
      const prompt = `Analyze this webpage content and provide the following in English, regardless of the original language:

1. A concise title
2. A brief description (max 200 characters)
3. Relevant tags that categorize the content (include both general category tags and specific topic tags)

If the content is not in English, please translate and analyze it appropriately.

URL: ${url}
Content: ${content}

Provide the response in the following JSON format:
{
  "title": "Brief, engaging title in English",
  "description": "Concise description in English (max 200 characters)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"] (5-7 relevant tags, starting with broader categories)
}

Make sure the tags are comprehensive and follow this structure:
- First tag: Main category (e.g., "technology", "science", "business")
- Second tag: Subcategory (e.g., "programming", "physics", "marketing")
- Remaining tags: Specific topics and themes`;

      const response = await openai.chat.completions.create({
        model: "gpt-3.5-turbo",
        messages: [
          {
            role: "system",
            content: "You are a helpful assistant that analyzes web content in any language and provides structured metadata in English. You excel at categorization and identifying key themes.",
          },
          {
            role: "user",
            content: prompt,
          },
        ],
        temperature: 0.7,
        max_tokens: 500,
      });

      const result = response.choices[0]?.message?.content;
      if (!result) {
        throw new Error("No response from OpenAI");
      }

      return JSON.parse(result) as AIAnalysis;
    } catch (error) {
      console.error('Error analyzing content:', error);
      throw new Error('Failed to analyze content');
    }
  }

  static async analyzeUrl(url: string): Promise<AIAnalysis> {
    const content = await this.fetchUrlContent(url);
    return this.analyzeContent(url, content);
  }
}