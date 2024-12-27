export interface Bookmark {
  id: number;
  url: string;
  title: string;
  description?: string;
  tags: string[];
  collections: string[];
  userId: number;
  dateAdded: Date;
  analysis?: {
    title?: string;
    summary?: string;
    credibilityScore?: number;
    tags?: string[];
    status?: string;
    lastUpdated?: string;
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
  id: number;
}
