import { z } from 'zod';

// Define the analysis status enum
export enum AnalysisStatus {
  Success = 'success',
  Error = 'error',
  InvalidUrl = 'invalid_url',
  RateLimited = 'rate_limited',
  Unreachable = 'unreachable',
  SystemError = 'system_error',
  Processing = 'processing'
}

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

export interface BookmarkMetadata {
  author?: string;
  publishDate?: string;
  lastModified?: string;
  mainImage?: string;
  wordCount?: number;
  analysisAttempts?: number;
  transcriptHighlights?: string[];
  status?: AnalysisStatus;
  error?: string;
  // Add video-specific metadata
  duration?: string;
  viewCount?: number;
  category?: string;
}

export interface BookmarkAnalysis {
  status?: AnalysisStatus;
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
  title?: string;
  description?: string;
  metadata?: BookmarkMetadata;
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