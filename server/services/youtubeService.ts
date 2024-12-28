import { google } from 'googleapis';
import fetch from 'node-fetch';
import { load } from 'cheerio';

export interface VideoDetails {
  title: string;
  description: string;
  transcript: string;
  author: string;
  publishDate: string;
}

export class YouTubeService {
  private static youtube = google.youtube('v3');

  private static async getVideoId(url: string): Promise<string | null> {
    try {
      const urlObj = new URL(url);
      if (urlObj.hostname.includes('youtube.com')) {
        return urlObj.searchParams.get('v');
      } else if (urlObj.hostname === 'youtu.be') {
        return urlObj.pathname.slice(1);
      }
      return null;
    } catch {
      return null;
    }
  }

  private static async fetchTranscript(videoId: string): Promise<string> {
    try {
      const response = await fetch(`https://www.youtube.com/watch?v=${videoId}`);
      const html = await response.text();
      const $ = load(html);

      // Extract transcript from captions
      const transcriptElements = $('[class*="caption-window"]');
      if (transcriptElements.length === 0) {
        return '';
      }

      const transcriptParts: string[] = [];
      transcriptElements.each((_, element) => {
        transcriptParts.push($(element).text().trim());
      });

      return transcriptParts.join(' ');
    } catch (error) {
      console.error('Error fetching transcript:', error);
      return '';
    }
  }

  private static async fetchVideoDetails(videoId: string): Promise<Partial<VideoDetails>> {
    try {
      const response = await fetch(`https://www.youtube.com/watch?v=${videoId}`);
      const html = await response.text();
      const $ = load(html);

      // Extract video metadata using meta tags
      const title = $('meta[property="og:title"]').attr('content') || '';
      const description = $('meta[property="og:description"]').attr('content') || '';
      const author = $('link[itemprop="name"]').attr('content') || 
                    $('span[itemprop="author"] link[itemprop="name"]').attr('content') || '';
      const publishDate = $('meta[itemprop="datePublished"]').attr('content') || '';

      return {
        title,
        description,
        author,
        publishDate
      };
    } catch (error) {
      console.error('Error fetching video details:', error);
      return {};
    }
  }

  public static async getVideoContent(url: string): Promise<VideoDetails | null> {
    try {
      console.log('[YouTube] Fetching content for:', url);
      const videoId = await this.getVideoId(url);
      if (!videoId) {
        console.error('[YouTube] Invalid YouTube URL:', url);
        return null;
      }

      console.log('[YouTube] Found video ID:', videoId);

      // Fetch both details and transcript in parallel
      const [details, transcript] = await Promise.all([
        this.fetchVideoDetails(videoId),
        this.fetchTranscript(videoId)
      ]);

      console.log('[YouTube] Successfully fetched video content');

      return {
        title: details.title || '',
        description: details.description || '',
        transcript: transcript || '',
        author: details.author || '',
        publishDate: details.publishDate || ''
      };
    } catch (error) {
      console.error('[YouTube] Error getting video content:', error);
      return null;
    }
  }
}