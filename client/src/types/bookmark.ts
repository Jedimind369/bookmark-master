import type { 
  AnalysisStatus, 
  ContentQuality, 
  VideoContent, 
  BookmarkAnalysis,
  Bookmark as SharedBookmark,
  CreateBookmarkDto as SharedCreateBookmarkDto,
  UpdateBookmarkDto as SharedUpdateBookmarkDto
} from '@shared/types/bookmark';

// Extend the shared types with client-specific fields
export interface Bookmark extends Omit<SharedBookmark, 'id'> {
  id: number; // Client uses number for IDs while shared uses string
}

export interface CreateBookmarkDto extends SharedCreateBookmarkDto {}

export interface UpdateBookmarkDto extends Omit<SharedUpdateBookmarkDto, 'id'> {
  id: number;
}

// Re-export shared types for convenience
export type {
  AnalysisStatus,
  ContentQuality,
  VideoContent,
  BookmarkAnalysis
};