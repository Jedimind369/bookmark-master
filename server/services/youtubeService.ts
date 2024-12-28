import { google } from 'googleapis';
import fetch from 'node-fetch';
import { load } from 'cheerio';

interface VideoDetails {
  title: string;
  description: string;
  transcript: string;
  author: string;
  publishDate: string;
  duration?: string;
  viewCount?: number;
  category?: string;
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

      // First try to get the transcript from captions
      const transcriptElements = $('[class*="caption-window"]');
      if (transcriptElements.length > 0) {
        const transcriptParts: string[] = [];
        transcriptElements.each((_, element) => {
          transcriptParts.push($(element).text().trim());
        });
        return transcriptParts.join(' ');
      }

      // If no captions, try to get auto-generated transcript
      const transcriptText = $('[class*="transcript-text"]').text().trim();
      if (transcriptText) {
        return transcriptText;
      }

      return '';
    } catch (error) {
      console.error('Error fetching transcript:', error);
      return '';
    }
  }

  private static async fetchVideoDetails(videoId: string): Promise<Partial<VideoDetails>> {
    try {
      // First try to get data using API
      const response = await fetch(`https://www.youtube.com/watch?v=${videoId}`);
      const html = await response.text();
      const $ = load(html);

      // Extract full description from meta tags and description element
      let description = '';
      const metaDescription = $('meta[property="og:description"]').attr('content') || '';
      const fullDescription = $('.ytd-video-description-text').text().trim() || 
                          $('#description-text').text().trim() || 
                          $('.description').text().trim();

      // Combine descriptions, preferring the longer one
      description = fullDescription.length > metaDescription.length ? fullDescription : metaDescription;

      // Get metadata
      const title = $('meta[property="og:title"]').attr('content') || '';
      const author = $('link[itemprop="name"]').attr('content') || 
                  $('span[itemprop="author"] link[itemprop="name"]').attr('content') || '';
      const publishDate = $('meta[itemprop="datePublished"]').attr('content') || '';

      // Extract additional metadata
      const duration = $('meta[itemprop="duration"]').attr('content') || '';
      const viewCountText = $('[class*="view-count"]').text().trim();
      const viewCount = viewCountText ? parseInt(viewCountText.replace(/\D/g, '')) : undefined;
      const category = $('meta[itemprop="genre"]').attr('content') || '';

      // If description is still empty or too short, try additional selectors
      if (description.length < 100) {
        const additionalDescription = $('#eow-description').text().trim() || 
                                  $('.watch-description-text').text().trim() || 
                                  $('[itemprop="description"]').text().trim();
        if (additionalDescription.length > description.length) {
          description = additionalDescription;
        }
      }

      return {
        title,
        description: description || 'No description available',
        author,
        publishDate,
        duration,
        viewCount,
        category
      };
    } catch (error) {
      console.error('Error fetching video details:', error);
      return {};
    }
  }

  static async getVideoContent(url: string): Promise<VideoDetails | null> {
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
        publishDate: details.publishDate || '',
        duration: details.duration,
        viewCount: details.viewCount,
        category: details.category
      };
    } catch (error) {
      console.error('[YouTube] Error getting video content:', error);
      return null;
    }
  }
}