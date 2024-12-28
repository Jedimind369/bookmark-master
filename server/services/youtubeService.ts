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
      console.log('[YouTube] Fetching transcript for video:', videoId);
      const response = await fetch(`https://www.youtube.com/watch?v=${videoId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch video page: ${response.status}`);
      }

      const html = await response.text();
      const $ = load(html);

      // Extract captions/subtitles
      const transcriptParts: string[] = [];

      // Try different selectors for transcript content
      const transcriptElements = [
        '.caption-window',
        '[class*="caption-window"]',
        '.ytp-caption-segment',
        '#caption-window-1'
      ].reduce((acc, selector) => {
        const elements = $(selector);
        if (elements.length > 0) {
          elements.each((_, el) => {
            const text = $(el).text().trim();
            if (text) acc.push(text);
          });
        }
        return acc;
      }, [] as string[]);

      // If no transcript found, try description
      if (transcriptElements.length === 0) {
        const description = $('meta[name="description"]').attr('content') || '';
        if (description) transcriptParts.push(description);
      } else {
        transcriptParts.push(...transcriptElements);
      }

      const transcript = transcriptParts.join(' ').trim();
      console.log(`[YouTube] Found transcript of length: ${transcript.length}`);
      return transcript;
    } catch (error) {
      console.error('[YouTube] Error fetching transcript:', error);
      return '';
    }
  }

  private static async fetchVideoDetails(videoId: string): Promise<Partial<VideoDetails>> {
    try {
      console.log('[YouTube] Fetching details for video:', videoId);
      const response = await fetch(`https://www.youtube.com/watch?v=${videoId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch video page: ${response.status}`);
      }

      const html = await response.text();
      const $ = load(html);

      // Extract video metadata using various selectors
      const title = $('meta[property="og:title"]').attr('content') ||
                   $('meta[name="title"]').attr('content') ||
                   $('title').text().split(' - YouTube')[0];

      const description = $('meta[property="og:description"]').attr('content') ||
                         $('meta[name="description"]').attr('content') ||
                         $('[itemprop="description"]').text();

      const author = $('meta[name="author"]').attr('content') ||
                    $('link[itemprop="name"]').attr('content') ||
                    $('[itemprop="author"] [itemprop="name"]').text() ||
                    $('.owner-name').text();

      const publishDate = $('meta[itemprop="datePublished"]').attr('content') ||
                         $('meta[property="article:published_time"]').attr('content') ||
                         $('meta[name="uploadDate"]').attr('content');

      const details = {
        title: title?.trim(),
        description: description?.trim(),
        author: author?.trim(),
        publishDate: publishDate?.trim()
      };

      console.log('[YouTube] Extracted video details:', details);
      return details;
    } catch (error) {
      console.error('[YouTube] Error fetching video details:', error);
      return {};
    }
  }

  public static async getVideoContent(url: string): Promise<VideoDetails | null> {
    try {
      console.log('[YouTube] Processing URL:', url);
      const videoId = await this.getVideoId(url);
      if (!videoId) {
        console.error('[YouTube] Invalid YouTube URL:', url);
        return null;
      }

      console.log('[YouTube] Valid video ID:', videoId);

      // Fetch both details and transcript in parallel
      const [details, transcript] = await Promise.all([
        this.fetchVideoDetails(videoId),
        this.fetchTranscript(videoId)
      ]);

      // Ensure we have at least minimal content
      if (!details.title && !details.description && !transcript) {
        console.error('[YouTube] Could not fetch any meaningful content');
        return null;
      }

      console.log('[YouTube] Successfully fetched video content');

      return {
        title: details.title || 'Untitled Video',
        description: details.description || '',
        transcript: transcript || '',
        author: details.author || 'Unknown Author',
        publishDate: details.publishDate || ''
      };
    } catch (error) {
      console.error('[YouTube] Error processing video:', error);
      return null;
    }
  }
}