export interface Bookmark {
  id: string;
  url: string;
  title: string;
  description?: string;
  tags: string[];
  collections: string[];
  userId: string;
  dateAdded: Date;
  analysis?: {
    title?: string;
    summary?: string;
    credibilityScore?: number;
    tags?: string[];
    status?: string;
    lastUpdated?: string;
    mainTopics?: string[];
    contentQuality?: {
      relevance: number;
      informativeness: number;
      credibility: number;
      overallScore: number;
    };
  }
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