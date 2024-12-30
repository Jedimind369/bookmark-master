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
  id: string;
}
