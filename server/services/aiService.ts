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
        .slice(0, 2000); // Allow slightly more content for better analysis

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
            content: "You are a specialized content analyzer. Your task is to analyze web content in any language and provide metadata in English. Focus on extracting the core meaning and themes, regardless of the original language.",
          },
          {
            role: "user",
            content: `Analyze this webpage content and translate/summarize into English:

Content from URL ${url}:
${content}

Return a JSON object with:
- title: A clear, concise English title (max 60 chars)
- description: A brief English summary (max 150 chars)
- tags: 3-5 relevant English tags, starting with the main category

Use this exact JSON structure:
{
  "title": "string",
  "description": "string",
  "tags": ["string"]
}`
          },
        ],
        temperature: 0.3, // Lower temperature for more consistent output
        max_tokens: 500,
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
        description: analysis.description.slice(0, 150),
        tags: analysis.tags.slice(0, 5).map(tag => tag.toLowerCase()),
      };
    } catch (error) {
      console.error('Error analyzing content:', error);
      throw new Error('Failed to analyze content');
    }
  }

  static async analyzeUrl(url: string): Promise<AIAnalysis> {
    try {
      const content = await this.fetchUrlContent(url);
      return await this.analyzeContent(url, content);
    } catch (error) {
      console.error('Error in analyzeUrl:', error);
      throw new Error('Failed to analyze URL');
    }
  }
}