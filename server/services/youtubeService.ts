import fetch from 'node-fetch';
import { load } from 'cheerio';

interface VideoMetadata {
  title: string;
  description: string;
  thumbnailUrl: string;
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

  static async getMetadata(url: string): Promise<VideoMetadata | null> {
    try {
      const videoId = await this.getVideoId(url);
      if (!videoId) {
        return null;
      }

      // Basic metadata that's always available
      return {
        title: `YouTube Video ${videoId}`,
        description: 'Video content from YouTube',
        thumbnailUrl: `https://i.ytimg.com/vi/${videoId}/maxresdefault.jpg`
      };
    } catch (error) {
      console.error('[YouTube] Error:', error);
      return null;
    }
  }
}