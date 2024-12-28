import fetch from 'node-fetch';
import { load } from 'cheerio';

interface VideoMetadata {
  title: string;
  description: string;
  thumbnailUrl: string;
  author: string;
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

  static async getVideoMetadata(url: string): Promise<VideoMetadata | null> {
    if (!url) {
      console.error('[YouTube] No URL provided');
      return null;
    }

    try {
      console.log('[YouTube] Fetching metadata for:', url);
      const videoId = await this.getVideoId(url);

      if (!videoId) {
        console.error('[YouTube] Invalid YouTube URL:', url);
        return null;
      }

      // Fetch the video page
      const response = await fetch(`https://www.youtube.com/watch?v=${videoId}`, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const html = await response.text();
      const $ = load(html);

      // Extract basic metadata using meta tags
      const title = $('meta[property="og:title"]').attr('content') || '';
      const description = $('meta[property="og:description"]').attr('content') || '';
      const thumbnailUrl = $('meta[property="og:image"]').attr('content') || 
                        `https://i.ytimg.com/vi/${videoId}/maxresdefault.jpg`;
      const author = $('link[itemprop="name"]').attr('content') || 
                    $('span[itemprop="author"] link[itemprop="name"]').attr('content') || '';

      console.log('[YouTube] Successfully fetched video metadata');

      return {
        title,
        description,
        thumbnailUrl,
        author
      };
    } catch (error) {
      console.error('[YouTube] Error fetching video metadata:', error);
      return null;
    }
  }
}