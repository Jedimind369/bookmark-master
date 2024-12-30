
import { Bookmark } from "@/types/bookmark";

export const fetchBookmarks = async (): Promise<Bookmark[]> => {
  const response = await fetch('/api/bookmarks');
  if (!response.ok) {
    throw new Error('Failed to fetch bookmarks');
  }
  return response.json();
};

export const updateBookmark = async (data: Partial<Bookmark>): Promise<Bookmark> => {
  const response = await fetch(`/api/bookmarks/${data.id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...data,
      tags: Array.isArray(data.tags) ? data.tags : [],
      collections: Array.isArray(data.collections) ? data.collections : []
    })
  });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to update bookmark: ${error}`);
  }
  return response.json();
};
