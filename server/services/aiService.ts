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
      const response = await openai.chat.completions.create({
        model: "gpt-3.5-turbo",
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content: "You are a helpful assistant that analyzes web content in any language and provides structured metadata in English. You excel at categorization and identifying key themes.",
          },
          {
            role: "user",
            content: `Analyze this webpage content and provide the following in English, regardless of the original language:

1. A concise title
2. A brief description (max 200 characters)
3. Relevant tags that categorize the content

URL: ${url}
Content: ${content}

Return only a JSON object with the following structure exactly:
{
  "title": "Brief, engaging title in English",
  "description": "Concise description in English",
  "tags": ["category", "subcategory", "specific-topic-1", "specific-topic-2", "specific-topic-3"]
}`
          },
        ],
        temperature: 0.7,
        max_tokens: 500,
      });

      const result = response.choices[0]?.message?.content;
      if (!result) {
        throw new Error("No response from OpenAI");
      }

      // Parse and validate the response
      let analysis: AIAnalysis;
      try {
        analysis = JSON.parse(result);
        if (!analysis.title || !analysis.description || !Array.isArray(analysis.tags)) {
          throw new Error("Invalid response format from OpenAI");
        }
      } catch (e) {
        console.error('Error parsing OpenAI response:', result);
        throw new Error('Failed to parse AI response');
      }

      return analysis;
    } catch (error) {
      console.error('Error analyzing content:', error);
      throw new Error('Failed to analyze content');
    }
  }

  static async analyzeUrl(url: string): Promise<AIAnalysis> {
    try {
      const content = await this.fetchUrlContent(url);
      return this.analyzeContent(url, content);
    } catch (error) {
      console.error('Error in analyzeUrl:', error);
      throw new Error('Failed to analyze URL');
    }
  }
}