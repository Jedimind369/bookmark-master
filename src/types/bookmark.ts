export type AnalysisStatus = 'success' | 'error' | 'invalid_url' | 'rate_limited' | 'unreachable' | 'system_error' | 'processing';

export interface Bookmark {
  id: string;
  url: string;
  title: string;
  description?: string;
  tags: string[];
  collections: string[];
  dateAdded: Date;
  dateModified?: Date;
  analysis?: {
    status?: AnalysisStatus;
    lastUpdated?: string;
    summary?: string;
    error?: string;
    retryable?: boolean;
    tags?: string[];
    contentQuality?: {
      relevance: number;
      informativeness: number;
      credibility: number;
      overallScore: number;
    };
    mainTopics?: string[];
    videoContent?: {
      transcript?: string;
      author?: string;
      publishDate?: string;
      viewCount?: number;
      duration?: string;
      category?: string;
    };
    recommendations?: {
      improvedTitle?: string;
      improvedDescription?: string;
      suggestedTags?: string[];
    };
    transcriptHighlights?: string[];
  };
  updateHistory?: Array<{
    timestamp: string;
    status: AnalysisStatus;
    message?: string;
  }>;
}

export interface CreateBookmarkDto {
  url: string;
  title: string;
  description?: string;
  tags?: string[];
  collections?: string[];
}

export interface UpdateBookmarkDto extends Partial<CreateBookmarkDto> {
  id: string;
}