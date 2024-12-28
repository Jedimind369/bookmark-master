export type AnalysisStatus = 'success' | 'error' | 'invalid_url' | 'rate_limited' | 'unreachable' | 'system_error' | 'processing';

export interface ContentQuality {
  relevance: number;
  informativeness: number;
  credibility: number;
  overallScore: number;
}

export interface VideoContent {
  transcript?: string;
  author?: string;
  publishDate?: string;
  viewCount?: number;
  duration?: string;
  category?: string;
}

export interface BookmarkAnalysis {
  status?: AnalysisStatus;
  lastUpdated?: string;
  summary?: string;
  error?: string;
  retryable?: boolean;
  tags?: string[];
  contentQuality?: ContentQuality;
  mainTopics?: string[];
  videoContent?: VideoContent;
  recommendations?: {
    improvedTitle?: string;
    improvedDescription?: string;
    suggestedTags?: string[];
  };
  transcriptHighlights?: string[];
}

export interface UpdateHistory {
  timestamp: string;
  status: AnalysisStatus;
  message?: string;
}

export interface Bookmark {
  id: string;
  url: string;
  title: string;
  description?: string;
  tags: string[];
  collections: string[];
  dateAdded: Date;
  dateModified?: Date;
  analysis?: BookmarkAnalysis;
  updateHistory?: UpdateHistory[];
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