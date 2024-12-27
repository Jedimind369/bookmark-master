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
    summary?: string;
    credibilityScore?: number;
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
